# JSReverser-MCP 集成手册（R3 协议过引擎）

本文件把 `JSReverser-MCP`（一个 Chrome DevTools 逆向 MCP 服务器）接入 `captcha-solver-router`，
作为 **R3 纯协议过** 的侦察 + 逆向引擎，并澄清它和 R1/R2 的边界。

---

## 1. 它在本 skill 里的角色

| 路线 | 执行引擎 | 是否用 JSReverser-MCP |
|---|---|---|
| **R1 平台出令牌**（reCAPTCHA/hCaptcha/Turnstile） | `scripts/solve.py`（调打码平台） | 否 |
| **R2 平台识别 + 浏览器自动操作**（滑块/点选/旋转） | `scripts/automate.py`（CloakBrowser/DrissionPage/Playwright） | 否（R2 的 stealth 由 `automate.py` 的 CloakBrowser 后端负责） |
| **R3 纯协议脚本（本地）** | **JSReverser-MCP（侦察）** + `js-reverse/captcha-slide-reverse` 工作流（算法知识） + 本地 Python/Node（交付） | **是** |

**关键边界（与 captcha-slide-reverse 的 SKILL 一致）**：
JSReverser-MCP 只用于**侦察与逆向**——还原加密算法、采样同轮参数、抓取干净基线。
最终交付必须是**浏览器无关**的 Python（requests）+ 本地 Node 小帮手（跑当前 fullpage/slide 的 `w` 生成）+ ddddocr/OpenCV（图片缺口/距离）。
**绝不让 MCP 或浏览器成为最终采集器**，否则风控一变就崩。

---

## 2. 把 MCP 接进客户端

JSReverser-MCP 是一个 Node 程序，入口 `build/src/index.js`。用**绝对路径**配置（避免工作目录变化找不到文件）。

### 2.1 Cursor / 通用 MCP JSON

```json
{
  "mcpServers": {
    "js-reverse": {
      "command": "node",
      "args": ["D:/pythonproject/git_pro/mcp_service/JSReverser-MCP/js-reverse-mcp-main/build/src/index.js"]
    }
  }
}
```

### 2.2 接管本机已开的 Chrome（远程调试，最常用）

先以远程调试端口启动 Chrome（Windows）：

```bash
"C:/Program Files/Google/Chrome/Application/chrome.exe" \
  --remote-debugging-port=9222 --user-data-dir="C:/tmp/chrome-mcp"
```

再在 MCP 配置里加 `--browserUrl`：

```json
{
  "mcpServers": {
    "js-reverse": {
      "command": "node",
      "args": [
        "D:/pythonproject/git_pro/mcp_service/JSReverser-MCP/js-reverse-mcp-main/build/src/index.js",
        "--browserUrl", "http://127.0.0.1:9222"
      ]
    }
  }
}
```

> `--browserUrl` 与 `--wsEndpoint` 二选一。不配置则 MCP 自己起一个隔离浏览器实例。

### 2.3 环境变量（可选）

```bash
cp .env.example .env
# DEFAULT_LLM_PROVIDER=gemini   # 配了才能用 understand_code / deobfuscate_code / risk_panel
# BROWSER_HEADLESS=true
# REMOTE_DEBUGGING_URL=http://localhost:9222
```

---

## 3. R3 三阶段工作流（MCP 充当侦察引擎）

```
┌─────────────┐   identify.py    ┌──────────────────────┐
│ 用户/网络样本 │ ──category=slide──▶│ captcha-solver-router │
└─────────────┘   platform=gt3    └──────────┬───────────┘
                                         路由判定 R3
                                                 │
                 ┌───────────────────────────────┼───────────────────────────┐
                 ▼ Phase A 侦察                    ▼ Phase B 还原              ▼ Phase C 交付
         JSReverser-MCP (DevTools)      captcha-slide-reverse 工作流     浏览器无关 Python/Node
         analyze_target / list_scripts    （算法知识库，见下方映射）       requests + ddddocr + 本地 JS
         hook fetch/xhr / get_hook_data   + 本地 VM/Node 复现 w/collect    → 距离/令牌 → 业务接口
         deobfuscate_code / get_paused   → 干净基线 + 同轮参数
```

### Phase A — 侦察（JSReverser-MCP，需要浏览器）

目标站首次接触，用最小链路抓干净基线（不要在 Hook 之前就堆 DOM）：

1. `new_page` / `navigate_page` 打开目标验证码页。
2. `analyze_target`（一键：collect + crypto/risk 分析 + hook 关联）看 `priorityTargets` / `requestFingerprints` / `signatureChain` / `actionPlan`。
3. `list_scripts` + `search_in_scripts`（关键词 `sign`/`token`/`w`/`collect`/`get_params`/`sendSA`）定位滑块算法脚本。
4. `create_hook` + `inject_hook`（`fetch`/`xhr`/`websocket`）→ 触发页面动作（手动滑一次）→ `get_hook_data` 拉请求与参数。
5. 必要：`set_breakpoint_on_text` + `get_paused_info` / `evaluate_on_callframe` 在断点处读 `w` 明文、`aeskey`、`collect` 原始结构。
6. 算法看不懂就 `understand_code` / `deobfuscate_code`（需配 LLM provider）或 `detect_crypto`。
7. `export_session_report` 沉淀证据。

> **反检测**：侦察浏览器可 `inject_stealth` 注入 stealth 脚本，降低被目标标记概率。这**只**用于侦察浏览器，与 R2 的 `automate.py --backend cloak` 是两回事。

### Phase B — 还原（captcha-slide-reverse 工作流 + 本地 VM）

打开对应的厂商工作流（在 JSReverser-MCP 仓库 `js-reverse/captcha-slide-reverse/references/`）：

| 厂商 | 工作流文件 | 核心交付 |
|---|---|---|
| 极验 GT3 | `geetest-gt3-workflow.md` | fullpage.9.x 生成 initial/pre `w`（同轮 `aeskey`）、slide.7.x 生成 final `w`、52 块乱序图还原找距离 |
| 极验 GT4 | SKILL.md「GT4 分支」 | `/load` 读 `lot_number/pow_detail` → `pow_msg/pow_sign` → AES+RSA 拼 `w` |
| 腾讯 TDC | SKILL.md「腾讯滑块分支」 | `env.js` 直跑 `TDC.getData(true)` 出 `collect`；`cap_union_new_verify` 带 `ans/pow` |
| 网易易盾 | `yidun-workflow.md` | `cb` 动态 + ddddocr 距离 + 轨迹 → `_0x3855dc` 出 `data` |
| 数美 | `shumei-workflow.md` | `get_params(x,track,times,rid)` 出 `ww/bb/vj/hq/wi/gq/vs` |
| 云片 | `yunpian-workflow.md` | `get_i_k()` / `get_i_k_position()` 出 `i/k/cb` |
| 360 天御 | `tianyu360-workflow.md` | 32 切片还原 + `rsa_1.js` 出 `report` |
| 顶象/鼎象 | SKILL.md「顶象分支」 | `o` 还原 `p1` + `greenseer.js` 出 `ac` |

> 所有厂商工作流强调同一铁律：**同轮复用** `token/session/c/s/aeskey/challenge`，否则 `param decrypt error` / `forbidden` / `4012 POSITION_MISMATCH`。

### Phase C — 交付（浏览器无关）

- HTTP 用 Python `requests`。
- 图片缺口/距离用 `PIL` + `ddddocr.slide_match` 或 OpenCV。
- 加密 `w`/`collect`/`data` 用**当前版本**的 JS 在本地 `vm`/`jsdom`/Node 小帮手跑（不要硬编码样本值）。
- 输出一份可运行脚本（含中间值日志），验证以服务端响应为准（GT3 `success:1`、GT4 `result:success`、易盾 PASS、数美 PASS、360 `data.result`…）。

---

## 4. 工具 → 步骤 映射速查

| 想做的事 | 用哪个 MCP 工具 |
|---|---|
| 一键摸清页面脚本与签名链 | `analyze_target` |
| 列出当前页加载的 JS | `list_scripts` |
| 在压缩代码里搜关键词 | `search_in_scripts` / `find_in_script` |
| 读某个脚本源码 | `get_script_source` |
| 在关键函数上设断点 | `set_breakpoint_on_text` / `set_breakpoint` |
| 断点命中后读作用域/变量 | `get_paused_info` / `evaluate_on_callframe` |
| 追踪某函数调用（不暂停） | `trace_function` / `hook_function` |
| 抓 fetch/xhr 参数 | `create_hook` + `inject_hook` → `get_hook_data` |
| 暂停在 XHR 上 | `break_on_xhr` + `get_request_initiator` |
| 解混淆 | `deobfuscate_code`（需 LLM） |
| 识别加密算法 | `detect_crypto` / `risk_panel` |
| 侦察浏览器加 stealth | `inject_stealth` / `list_stealth_presets` |
| 导出分析报告 | `export_session_report` |
| 页面动作（触发登录/提交） | `navigate_page` / `click_element` / `type_text` / `take_screenshot` |

---

## 5. 端到端 Runbook：极验 GT3（R3）

前提：已按 §2 配好 JSReverser-MCP，且目标站出现 GT3 信号
（`register-slide` → `gettype.php` → `fullpage.9.x` → `/get.php` → `/ajax.php`）。

```text
① 路由：identify.py 判定 category=slide, platform=gt3 → 走 R3
   python scripts/identify.py --text "register-slide gettype.php fullpage.9.x slide.7.x ajax.php w"

② 侦察（MCP，浏览器打开目标页）
   new_page(目标URL)
   analyze_target()                      # 看 priorityTargets / signatureChain
   search_in_scripts("fullpage")        # 定位 fullpage.9.x
   create_hook(fetch) + inject_hook()   # 钩住业务/极验请求
   # 手动触发一次滑块 → get_hook_data() 抓 initial/get.php 的 w 与响应

③ 还原（对照 references/geetest-gt3-workflow.md）
   - 本地 VM 跑 fullpage.9.x：initial /get.php 的 w（导出同轮 aeskey）
   - 同 aeskey 生成 pre /ajax.php 的 w（须返回 {"result":"slide"}）
   - slide.7.x 生成 final w（距离来自 52 块乱序图还原 + ddddocr）
   - 所有 c/s/challenge/aeskey 同轮

④ 交付（浏览器无关）
   python gt3_solver.py                # requests + 本地 Node 帮手 + ddddocr
   # 成功拿到 validate / seccode → 交给业务 validate|jordan
```

**高频失败**（详见工作流文件）：
- pre `/ajax.php` `param decrypt error` → initial 与 pre 的 `aeskey` 不是同一轮。
- final `forbidden` → final 的 `aa/ep.tm/距离/轨迹/challenge/c/s` 不同轮。
- 距离不准 → 52 块乱序图还原顺序错，提交 `target_x - 6` 这类经验偏移需复核。

---

## 6. 与 R1/R2 的衔接

- **R1（平台令牌）**：不碰 MCP。直接 `solve.py --platform yescaptcha --type recaptcha_v2 ...`。
- **R2（自动拖拽）**：不碰 MCP 侦察。直接 `automate.py --backend cloak --op slide --offset 128 ...`。
  若 R2 拿到的距离想换成「自己协议算」而非平台双图，则先走本文件的 R3 Phase B/C 算出距离，再喂给 `automate.py --op slide --offset <算出的距离>`。
- **R3（协议）**：本文件全流程。MCP 只在 Phase A 出现。

> 一句话：**MCP 是 R3 的「眼睛」（看算法、采样本），不是「手」（手是 R2 的 automate.py，或 R3 的 Python 请求）。
