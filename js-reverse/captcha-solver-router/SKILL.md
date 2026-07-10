---
name: captcha-solver-router
description: >-
  验证码应对路由器。当目标站点出现任意验证码时，先识别类型，再分析可行过法（R1 token / R2 打码+自动化 / R3 纯协议）。
  **强制停步**：用户确认打码平台+captchaType、确认 config.json 路径（project_detect/preflight）、确认产物落盘路径后，才可 setup/付费调用/写项目文件。
  **已实测通过**：reCAPTCHA v2 token、reCAPTCHA v2 九宫格、极验 GT3、网易易盾滑块/文字点选。
  **已接入待稳定**：网易易盾图标点选、京东 JCAP（`jd-jcap-slide` 滑块、`jd-login-captcha` 多题型自动识别）。
  亦支持 reCAPTCHA/hCaptcha/Turnstile/CF5s、极验 GT3/GT4、腾讯 TDC/TCaptcha、数美、云片、360 天御、顶象滑块等。
  不要用于仅需泛化定位 sign/token 入口、纯 DevTools hook、或非验证码 WAF/cookie 挑战。
argument-hint: "[目标 URL / 类型 / 平台: yescaptcha|bingtop|jfbym] [动作: identify|route|solve|automate|protocol]"
compatibility: "全 Python 技术栈。R1/R2 需项目根 config.json（setup.py 配置密钥）；R2 浏览器自动化见 scripts/automate.py（CloakBrowser/Playwright/DP + browser_stealth）；R3 见 references/mcp-integration.md + captcha-slide-reverse。"
---

# captcha-solver-router

把「遇到验证码怎么办」从拍脑袋变成可复用、可选择的决策流程：先识别类型，再按类型匹配最适合的打码平台与过法，**经用户确认后**再配置、编码与实测。

## 已验证类型（本机实测）

> 在测试项目 `测试验证码skill` + 本机 `config.json` + Playwright 本机 Chrome + `browser_stealth` 下跑通。其他站点需按同流程复测。

| 验证码 | 厂商 | 路线 | 平台 / captchaType | CLI | Demo | 状态 |
|---|---|---|---|---|---|---|
| reCAPTCHA v2 Token | Google | R1→R2 | YesCaptcha `NoCaptchaTaskProxyless` + `--op token` | `--op token` | [api2/demo](https://www.google.com/recaptcha/api2/demo) | ✅ **已通过**（打码 + 注入 + Submit 验证） |
| reCAPTCHA v2 九宫格 | Google | R2 | YesCaptcha `ReCaptchaV2Classification` + `recaptcha-grid` | `--op recaptcha-grid` | [api2/demo](https://www.google.com/recaptcha/api2/demo) | ✅ **已通过**（手动触发挑战后自动点选） |
| GT3 滑动拼图 | 极验 | R2 | BingTop `1310` + `gt3_restore` + `--op slide` | `solve.py --gt3-restore` + `automate.py --op slide` | [demos.geetest.com](https://demos.geetest.com/test.html) | ✅ **已通过**（还原双图识别 + 拟人拖拽） |
| 滑动拼图（滑块） | 网易易盾 | R2 | BingTop 双图滑块 + `yidun-slide` | `--op yidun-slide` | [jigsaw](https://dun.163.com/trial/jigsaw) | ✅ **已通过** |
| 文字点选 | 网易易盾 | R2 | BingTop `13152` + `yidun-click` | `--op yidun-click` | [picture-click](https://dun.163.com/trial/picture-click) | ✅ **已通过** |
| 图标点选 | 网易易盾 | R2 | BingTop 双图（`13202` 理想 / `13242` 备选）+ `icon-click` | `--op icon-click --click-provider yidun` | [icon-click](https://dun.163.com/trial/icon-click) | 🔧 **已接入**，注意冰拓 type 开通与限流 |
| 京东登录 JCAP（旋转/轨迹/滑块） | 京东 | R2 | BingTop **按题型**：旋转 `11201`、轨迹 `3002`、滑块 `1310` + `jd-login-captcha` | `--op jd-login-captcha` | [passport.jd.com](https://passport.jd.com/new/login.aspx) | 🔧 **已接入**，见 `references/jd-login-captcha.md` |

**R2 共性能力（上述易盾项均已启用）**：本机 Chrome、`browser_stealth`（webdriver 隐藏 + CDP）、拟人鼠标（贝塞尔移动/拖拽）、`preflight.py` 配置预检。

**本地快速复测**（在测试项目目录）：

```bash
python full_workflow_test.py              # 全流程（预检+识别+离线识别+易盾 E2E）
python full_workflow_test.py --quick      # 仅预检+识别+GT3 打码（无浏览器）
python yidun_jigsaw_test.py --embed       # 单项：易盾滑块
python yidun_click_test.py --embed        # 单项：易盾文字点选
python recaptcha_manual_test.py --demo    # 单项：reCAPTCHA 九宫格（需手动触发挑战）
python icon_click_test.py --embed         # 单项：易盾图标点选
```

## 人机协同流程（推荐）

面向「用户提供目标站 → 最终能过验证码」的完整协作路径。Agent **每步停步确认**，不要跳过用户决策。

**禁止事项（Agent 违反即视为流程失败）**：
- 未获用户明确确认 → **不得**选定打码平台、`captchaType`、路线
- 未与用户确认 `config.json` 路径 → **不得**运行 `setup.py` / 调付费 `solve.py`
- 未运行 `project_detect.py` 并获用户确认落盘路径 → **不得**在用户项目内创建/修改文件
- 不得把密钥、业务密码写入对话；不得默认把代码写进 skill 目录（`scripts/` 仅放通用引擎）

```
用户提供目标
    ↓
⓪ 确认工作区：项目根、config 路径、框架探测（project_detect）
    ↓
① 收集材料 & 识别类型 → 用户确认类型/厂商
    ↓
② 枚举过法路线（R1/R2/R3）→ 用户选路线
    ↓
③ 推荐打码平台 & captchaType 候选 → 用户明确确认平台+类型
    ↓
④ 确认平台账号 & 研读接口文档
    ↓
⑤ 与用户确认 config.json 路径 → 引导 setup/preflight → 用户回复「已配置」
    ↓
⑥ 展示产物路径表 → 用户确认 → 再创建测试脚本/集成模块
    ↓
⑦ 本地实测 & 迭代
```

### ⓪ 确认工作区（config 路径 + 项目框架）

**在任何识别/写代码之前**，先弄清「配置写哪、代码写哪」：

```bash
cd <用户当前工作目录>
python <skill>/scripts/project_detect.py --vendor <厂商> --route R2
# 或预检时附带：
python <skill>/scripts/preflight.py --route R2 --with-project --vendor jcap --json
```

向用户展示并**必须确认**：

| 项 | 说明 | 默认规则 |
|---|---|---|
| **project_root** | 业务项目根 | 由 `project_detect` 从 cwd 向上推断（`.git` / `pyproject.toml` 等） |
| **config.json** | 打码密钥与 Chrome 路径 | 优先 `CAPTCHA_ROUTER_CONFIG` → 向上查找已有 `config.json` → 否则 `project_root/config.json` |
| **禁止** | skill 内 `scripts/config.json` | 密钥与业务测试脚本**不**进 skill 目录 |

**标准确认话术**：

> 探测到你的项目根为 `<project_root>`。建议 `config.json` 放在 `<resolved 或候选路径>`。  
> 验证码测试脚本建议放在 `<test_script_recommended>`。是否同意？如需修改请直接给出绝对路径。

用户确认路径后，再执行 `preflight.py --init` / `setup.py`（在**已确认的目录**下运行，或设置 `CAPTCHA_ROUTER_CONFIG`）。

### ① 收集材料 & 识别类型

向用户索取（能拿多少拿多少）：

- **目标 URL**（验证码出现的页面）
- **截图** 或 **HAR / 关键网络请求**（register、get、verify、ajax 等）
- 是否**自有/授权**业务（合规边界）

执行识别：

```bash
python scripts/identify.py --text "<html/js/请求摘要>"
# 或 --har capture.har
```

输出 `category`（token/slide/click/…）、`platform`（gt4/yidun/tencent/jcap…）、`confidence`、`evidence`。识别不出 → **向用户补样本，勿硬猜**。

**停步**：用表格列出识别结果，请用户确认「验证码类型 + 厂商」是否正确；用户否认或补充样本前，**不得**进入路线推荐或写代码。

### ② 枚举路线 → 用户确认

| 路线 | 含义 | 典型场景 |
|---|---|---|
| **R1** | 平台直接返回 token | reCAPTCHA / hCaptcha / Turnstile / CF5s |
| **R2** | 打码平台识别 + 浏览器自动化 | 滑块、点选、旋转、轨迹 |
| **R3** | 纯协议脚本（无第三方） | 滑块/部分点选，愿投入逆向 |

用表格向用户呈现每条路线的：**成本、稳定性、是否要浏览器、是否暴露图片给第三方、工作量**。用户明确选定 **路线** 后再往下；**不得**替用户默认 R2/R3。

### ③ 推荐平台 & captchaType → **用户明确确认**

按类型给出首选（详见 `references/platforms.md` §2.3）：

| 类型 | 首选平台 | 备注 |
|---|---|---|
| Token 类 | YesCaptcha（JFBYM 备选） | R1 only |
| 滑块/点选/旋转 | BingTop / JFBYM | R2；**captchaType 因账号而异，须试跑** |
| 易盾滑块/点选 | 内置 `yidun-slide` / `yidun-click` / `icon-click` | 已验证项见上表 |
| 京东 JCAP 登录多题型 | BingTop **按识别类别**（`bingtop_types.resolve_captcha_type`） | 旋转 `11201`/轨迹 `3002`/滑块 `1310`；**勿用** `11203`/`30013` 等不存在 ID | `jd-login-captcha` + `references/jd-login-captcha.md` |

**必须告知用户**：冰拓 `captchaType` 须对照[官方类型表](https://www.bingtop.com/type/)与 `scripts/bingtop_types.py`；与账号开通范围绑定。京东登录等多题型场景**按识别类别**选 type（旋转≠轨迹）。类型错误会返回 `captcha type error`。

**停步（强制）**：用 `AskQuestion` 或等价方式让用户**明确选择**：

1. **打码平台**：`yescaptcha` / `bingtop` / `jfbym` / 其他（外接）
2. **captchaType**（冰拓/JFBYM 图片类）：给出 1～3 个**候选 ID** + 说明，由用户选定；未选定前**不得**调用 `solve.py`
3. **是否已有该平台账号**；无账号则改推 R3 或引导注册

禁止 Agent 在未确认时：擅自用 `config.json` 里「已有密钥的平台」代替用户选择；擅自写死 `1310` 等类型 ID。

用户确认：**平台名称 + captchaType（若适用）+ 路线** 三者齐全后，才可进入 ④⑤。

### ④ 平台账号 & 接口文档

询问用户：**是否已有**打码平台账号？

- **有** → 请用户提供**官方文档链接**（或 Agent 用 WebFetch 抓取），弄清：
  - 鉴权字段（`clientKey` / `username+password` / `token`）
  - 请求字段（如冰拓 `captchaData` + `subCaptchaData` 均为**图片 base64，无 data-uri 前缀**）
  - 响应字段（`recognition` 坐标格式、`gRecaptchaResponse` 等）
  - 限流与计费规则
- **无** → 说明 R3 不依赖第三方；或引导注册并说明计费
- **外接平台** → 走 `learn_platform.py` + `adapters/template.py` 插件机制

### ⑤ 引导本地配置（**与用户确认路径后**）

密钥**只进用户确认的 `config.json` 路径**，**绝不进对话**：

```bash
cd <用户确认的项目根或 config 所在目录>
# 可选：set CAPTCHA_ROUTER_CONFIG=D:\path\to\config.json
python <skill>/scripts/preflight.py --init
python <skill>/scripts/setup.py
python <skill>/scripts/preflight.py --route R2 --platform bingtop --json
```

`config.json` 还需（R2 推荐）：

```json
"automation": {
  "chrome_executable": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
}
```

**停步**：`preflight` 未通过或用户未回复「已配置」前，**禁止**调用 `solve.py` / 付费识别。`setup.py` 启动时会打印 `配置将写入: <path>`，Agent 应把该路径复述给用户核对。

用户回复「已配置」后，Agent 再调付费接口。调试冰拓时可设 `BINGTOP_DEBUG=1` 查看请求摘要与响应（见 `adapters/bingtop.py`）。

### ⑥ 编写代码（**先确认路径，再创建文件**）

**先**运行 `project_detect.py`（或 `preflight --with-project`），向用户展示：

| 产物 | 推荐位置 | 说明 |
|---|---|---|
| 测试脚本 | `artifacts.test_script_recommended` | 薄封装：调用 skill 的 `automate.py` / `solve.py` |
| 业务集成 | `artifacts.integration_module_recommended` | 可选；嵌入爬虫/登录流程 |
| 通用引擎 | `skill/scripts/automate.py` 等 | **仅引用，不复制**到用户项目 |

**停步**：用户确认「创建哪些文件、最终路径」后，再写入。若用户只要一次性实测，可只建测试脚本；若已有 `tests/` 目录，优先放 `tests/`。

按路线生成最小可跑产物：

| 路线 | 产物 |
|---|---|
| R1 | 项目内调用 `solve.py` 的薄脚本 + 业务请求回填 token |
| R2 | 项目内 `*_test.py` 调 `automate.py`（`--op yidun-slide` / `jd-login-captcha` / `jd-jcap-slide` 等） |
| R3 | 移交 `captcha-slide-reverse` + `mcp-integration.md`；项目内仅放协议脚本目录（用户确认路径） |

原则：**厂商无关流程 + 可插拔 Provider**（新厂商逻辑优先放 skill `scripts/`，项目内只放参数与 URL）；坐标缩放与打码上传图尺寸对齐（`coord_image_wh`）。

### ⑦ 本地实测 & 迭代

1. 在项目目录放 `config.json`，运行对应测试脚本或 `automate.py`
2. 成功标准：页面验证通过（如 `yidun_success: true`）或业务接口 200
3. 失败时查 `references/platforms.md` 失败模式表；易盾滑块见 `yidun-r2-automation.md`；图标点选见 `icon-click-r2.md`；京东登录见 `jd-login-captcha.md`
4. 冰拓限流 → 降低 `--click-max-rounds`、间隔重试；type 错误 → 换 captchaType 而非刷接口

---

**相较你描述的流程，建议补充的三点**：

1. **第 0 步预检**：任何付费调用前先 `preflight.py`，避免缺密钥/缺 Chrome 白跑。
2. **captchaType 试跑**：平台与类型须用户确认后，用一张样本图探测（勿写死 ID）；图标点选与文字点选 BingTop 类型不同。
3. **明确成功标准与调试开关**：约定 JSON 输出字段（`ok` / `yidun_success`）、`BINGTOP_DEBUG`、坐标缩放日志，方便迭代而非反复猜。

内置 Agent 用的「五步工作流」（Identify → Route → Match → Present → Execute）与上表 **①～⑦ 人机协同流程** 一一对应；对用户说话时走 ①～⑦，对内执行时可映射到原五步。

## 与 captcha-slide-reverse 的关系

- **本 skill 负责「识别 + 路由 + 调平台」**，是上层调度器。
- **JSReverser-MCP 是 R3 的「侦察引擎」**：当路由判定走纯协议路线（R3）时，用它的 DevTools 工具（`analyze_target` / `hook` / `get_script_source` / `deobfuscate_code`）还原加密算法、采样同轮参数、抓干净基线。详见 `references/mcp-integration.md`。
- **captcha-slide-reverse 负责「协议过」的具体逆向知识**：其 `js-reverse/captcha-slide-reverse/references/` 下按厂商（GT3/GT4/腾讯/易盾/数美/云片/360/顶象）给出请求链与算法工作流。本 skill 不重复写各平台滑块的加密细节，只负责路由与衔接。
- 滑块类有两条腿：平台双图滑块（R2，省事但依赖第三方、暴露账号）+ 协议脚本（R3，零边际成本但逆向贵、易随风控失效）。

## 首次配置（密钥引导）

本 skill 调平台需要密钥。**密钥只在你本地项目目录 `config.json` 里，不在 skill 目录，绝不进入聊天或版本库。**

- **配置位置**：在**用户确认的项目目录**放置 `config.json`（已加入 `.gitignore`）；运行前先 `python project_detect.py` 展示路径并获用户确认。
- **查找顺序**：环境变量 `CAPTCHA_ROUTER_CONFIG` → 从 cwd 向上查找 `config.json`（跳过 skill/scripts 内部）→ 默认 `project_root/config.json`。
  1. `python scripts/preflight.py --init` — 从 `config.example.json` 生成空骨架；
  2. `python scripts/setup.py` — 交互式填写密钥；
  3. `python scripts/preflight.py --route R1`（或 `R2`/`R3`）— 验证还缺什么。
- **Agent 发现配置缺失时的标准话术**（不要索要明文密钥）：
  > 检测到本地尚未配置打码平台密钥。请在本机终端运行 `cd <skill>/scripts && python setup.py`，按向导填入你**已有**的平台密钥（输入不回显）。配置完成后告诉我「已配置」，我再继续调平台。**请勿在对话里粘贴 clientKey / 密码 / token**；如误发请去对应平台重置。
- **缺配置时主动问用户**：「你已有哪家平台的密钥？我帮你写进本地 `config.json`（不要发到聊天里）」，然后引导跑 `setup.py` 或手动编辑 `config.json`（参考 `config.example.json`）。绝不在对话里索要/接收明文 clientKey / 密码 / token。
- **用户没有任何平台密钥**：仍可走 **R3 纯协议路线**（移交 `captcha-slide-reverse`），不依赖第三方；运行 `python scripts/preflight.py --route R3` 检查 MCP/Chrome 即可。
- `scripts/.gitignore` 已排除 `config.json`；`solve.py` 读取顺序：`config.json` > 环境变量。
- 如用户误把密钥发到对话里，提醒其去对应平台重置。

## 第 0 步：配置预检（Preflight）

**在执行识别之后的任何路线前**，先检查本地基础配置是否就绪。缺什么就引导用户补什么，不要假设已配好。

```bash
cd scripts
python preflight.py              # 全量预检
python preflight.py --route R1     # 只查 token 路线所需
python preflight.py --route R2 --backend cloak
python preflight.py --platform yescaptcha
python preflight.py --init         # 生成 config.json 骨架
python preflight.py --json         # 机器可读 JSON 信封
```

| 检查项 | 影响路线 | 缺失时引导 |
|---|---|---|
| `config.json` 存在 | R1/R2 | `preflight.py --init` 或 `setup.py` |
| YesCaptcha/JFBYM/BingTop 密钥 | R1/R2 | `setup.py`（不回显）或环境变量 |
| CloakBrowser/DP/Playwright | R2 | `pip install ...`（见 preflight 输出） |
| Chrome `:9222` 远程调试 | R2/R3 | 见 `references/mcp-integration.md` §2.2 |
| JSReverser-MCP | R3 | 见 `references/mcp-integration.md` §2 |

**Agent 行为规则**：
1. 用户选定 R1/R2 且 `preflight` 报密钥缺失 → **停步**，与用户确认 config 路径后引导 `setup.py`，等用户确认后再 `solve.py`。
2. 用户选定 R3 → 不要求打码密钥，但检查 MCP + Chrome 引导。
3. 仅 Router 识别（第 1 步）→ 无需密钥，可直接 `identify.py`；但仍建议跑 `project_detect` 确认工作区。
4. `solve.py` 调平台前会自动预检；失败时 stderr 输出完整 `guide`。
5. **创建用户项目内任何文件前** → 必须 `project_detect.py` + 用户确认路径（见 ⓪⑥）。
6. **调用付费 API 前** → 必须用户已确认「平台 + captchaType」（见 ③）。

```bash
python project_detect.py --vendor yidun --route R2
python preflight.py --route R2 --platform bingtop --with-project --vendor yidun --json
```

## 触发条件

出现任一信号时启用：

1. 用户说「过验证码」「识别不了验证码」「这个滑块怎么过」「reCAPTCHA/hCaptcha/Turnstile 怎么搞」「点选验证码怎么点」「旋转验证码」「图文/计算题验证码」。
2. 目标页面出现验证码组件或网络请求里的验证码信号（见 `references/type-signals.md`）。
3. 用户要求对比/选择打码平台，或要求调用打码平台 API。

不要在这些场景启用：

1. 只泛化定位某个 sign/token 入口（转对应入口定位 skill）。
2. 只要浏览器 hook 脚本（转 `browser-hook-snippets`）。
3. 只做通用 Node.js 补环境（转 `env-patch`）。
4. 非验证码的 WAF/cookie 挑战（如 Akamai/Imperva 纯风控，不在此范围）。

## 五步工作流

### 第 1 步：识别类型（Identify）

从用户提供的 HTML/JS/网络请求/HAR/截图文字里析出验证码类型。

- 优先用 `scripts/identify.py` 做启发式匹配：`python scripts/identify.py --text "<html/js/network dump>"` 或 `--har har.json`。
- 信号表见 `references/type-signals.md`。
- 输出：`category`（token/slide/click/rotate/image/track）、`platform`（具体厂商，如 gt4/tencent/yidun…）、`confidence`、`evidence`。
- 识别不出时，向用户要一个验证码截图或关键 JS/网络样本，不要硬猜。

### 第 2 步：枚举可行路线（Route）

对每个类型，按下面三类路线枚举（不是每个类型都适用全部）：

- **R1 — 平台 token 协议**：平台直接返回令牌（reCAPTCHA/hCaptcha/Turnstile 的 `gRecaptchaResponse`/`h-captcha-response`/`cf-turnstile-response`）。无需浏览器点击，HTTP 即可。即「协议过」由平台代劳。
- **R2 — 平台识别 + 浏览器自动操作**：平台返回坐标/距离(px)/角度/答案，用反爬浏览器驱动自动拖滑块、点坐标、旋转。即「自动化点击过」。驱动选型见 `references/automation.md`，统一引擎见 `scripts/automate.py`，支持 **CloakBrowser**（源码级隐形 Chromium，强反爬首选）/ **DrissionPage（DP）**（轻量自带反检测）/ **Playwright**（原生，需自加 stealth）。
- **R3 — 纯协议脚本（本地，JSReverser-MCP 侦察）**：用 `JSReverser-MCP` 的 DevTools 工具还原加密算法、采样同轮参数（Phase A 侦察），对照 `captcha-slide-reverse` 的厂商工作流在本地 VM/Node 复现 `w`/`collect`/`data`（Phase B 还原），最终用**浏览器无关**的 Python（requests）+ ddddocr/OpenCV 交付（Phase C）。不依赖第三方、零边际成本，但逆向成本高、随风控易失效。仅滑块/部分点选可行。完整流程见 `references/mcp-integration.md`。

### 第 3 步：按类型匹配最适合的平台（Match）

用户选择「按类型匹配」，则按下面矩阵定默认首选（三家都写进 `references/platforms.md` 知识库，可随时切换）：

| 类型 | 可行路线 | 首选平台 | 理由 |
|---|---|---|---|
| reCAPTCHA v2/v3、hCaptcha、FunCaptcha、Turnstile、CF5s | R1 | **YesCaptcha**（JFBYM 备选） | token 类最强，有中国节点，`createTask`/`getTaskResult` 标准化 |
| 8 类滑块（GT3/GT4/腾讯/易盾/数美/云片/360/顶象） | R2 或 R3 | R2→**BingTop/JFBYM**（双图滑块返回 px）；易盾 R2 内置 `yidun-slide`；R3→`captcha-slide-reverse` | YesCaptcha 无滑块类；BingTop 1310 易盾双图；距离换算见 `yidun-r2-automation.md` |
| 点选/坐标/文字点选/语序/空间推理/九宫格 | R2 | **BingTop / JFBYM** | 返回坐标，浏览器点击；图标点选用 `--op icon-click`（Provider 可插拔） |
| 旋转 | R2 | **BingTop / JFBYM** | 返回角度，换算距离拖拽 |
| 图文/字符/计算题 | R1-like（ImageToText） | **BingTop / JFBYM**（YesCaptcha `ImageToTextTask` 也可） | 返回答案字符串 |
| 轨迹 | R2 或 R3 | **BingTop / JFBYM** | 返回轨迹点回放 |

> 价格量级（详见 `references/platforms.md`）：YesCaptcha 1 元=1000 点，token ¥0.015–0.03；JFBYM 双图滑块 ¥0.01、recaptcha ¥0.032、CF ¥0.02；BingTop 低至 ¥0.001/图。

### 第 4 步：把选项交给用户（Present）

用表格列出每条路线，至少包含：

- **成本**：单次价格 / 是否零成本（R3）。
- **稳定性**：平台人工/AI 波动 vs 协议随风控失效。
- **是否需要浏览器**：R1 否，R2 是，R3 否（但生成脚本需 Node/execjs）。
- **是否暴露账号**：R1/R2 需把图片/站点交给第三方；R3 不暴露。
- **实施工作量**：R1/R2 接 API 快；R3 需逆向。

让用户选定路线 + 平台 + captchaType。若用户要「按类型匹配」则给出首选作为**默认推荐**，仍须用户点选确认，不得自动执行。

### 第 5 步：执行（Execute）

- **运行前先跑预检**：`python scripts/preflight.py --route R1|R2|R3`；密钥缺失则引导 `python scripts/setup.py`，**不要直接调付费接口**。
- **R1/R2 调平台**：用 `scripts/solve.py` 统一客户端：
  - `python scripts/solve.py --platform yescaptcha --type recaptcha_v2 --sitekey XXX --url XXX`
  - `python scripts/solve.py --platform jfbym --type slide --bg bg.png --slice slice.png`
  - `python scripts/solve.py --platform bingtop --op slide --captcha-type <按platforms.md§2.3.1> --image bg.png --slice slice.png [--gt3-restore]`
  - 极验 GT3 图片：先用 `scripts/gt3_capture.py` 从 slide `get.php` JSONP 下载 bg/slice（协议层，见 `captcha-slide-reverse` GT3 工作流），再 `--gt3-restore` + 第三方识别；**R2 距离识别优先 BingTop/JFBYM，不用 ddddocr**。
  - 冰拓 `captchaType` **不可写死**，须对照冰拓文档与样本试跑（`references/platforms.md` §2.3.1）。
  - 密钥从**用户项目** `config.json`（`config_paths.resolve_config_path`）或环境变量读取。
- **R2 浏览器自动操作**：拿到坐标/距离/角度后，用 `scripts/automate.py` 多后端引擎执行拟人拖拽/点击/旋转，再把结果回填业务请求。Chrome 路径由用户在 `config.json` → `automation.chrome_executable` 配置（`setup.py`），勿写死本机路径。驱动选型与拟人轨迹模板见 `references/automation.md`。
  - **网易易盾文字点选**：`--op yidun-click`（见 `references/automation.md` §4.5）
  - **网易易盾滑动拼图**：`--op yidun-slide`（见 `references/yidun-r2-automation.md`）
  - **通用图标点选**：`--op icon-click --click-provider yidun`（见 `references/icon-click-r2.md`；Demo [图标点选](https://dun.163.com/trial/icon-click)）
  - **京东登录 JCAP（旋转/轨迹/滑块）**：`--op jd-login-captcha`（见 `references/jd-login-captcha.md`）
- **R3 协议脚本**：按 `references/mcp-integration.md` 的三阶段走——先用 `JSReverser-MCP`（需配好 MCP 客户端，见该文件 §2）在浏览器里侦察还原算法，再对照 `captcha-slide-reverse` 的厂商工作流本地复现，最后用**浏览器无关**的 Python/Node 交付脚本。本 skill 只负责路由、衔接与把厂商工作流指对位置，不重写其逆向细节。

## 平台知识库

三家的精确接口地址、鉴权方式、请求/响应字段、代码示例、类型→平台映射全部在 `references/platforms.md`。接入时严格按文档字段名，不要自创参数。

**R2 自动化驱动（反爬浏览器）选型与拟人交互模板**见 `references/automation.md`；统一执行引擎见 `scripts/automate.py`（基于你指定的 Python 技术栈，支持 CloakBrowser / DrissionPage / Playwright 多后端）。
**网易易盾 R2 自动化（文字点选 + 滑动拼图）**见 `references/automation.md` §4.5 与 `references/yidun-r2-automation.md`。
**京东 PC 登录 JCAP（多题型自动识别）**见 `references/jd-login-captcha.md`。
**R3 协议过（JSReverser-MCP 侦察 + 浏览器无关交付）** 见 `references/mcp-integration.md`。

## 外接打码平台（插件机制）

本 skill 内置 yescaptcha / bingtop / jfbym，但**允许用户外接任意打码平台**，无需改 skill 源码。所有平台统一实现 `adapters/base.py` 的 `BaseSolver` 接口，由 `solve.py` 通过注册表自动发现。

### 两种外接方式

1. **丢进目录（推荐）**：把写好的适配器 `.py` 放进 `scripts/adapters/`，重启即被自动发现，`--platform <name>` 直接可用。
2. **外部路径**：平台文件放别处时，在 `scripts/config.json` 的 `external_adapters` 登记绝对路径列表（见 `config.example.json`）。

### 用户自己写适配器

复制模板改四样即可（详见 `scripts/adapters/template.py`）：

```bash
cp scripts/adapters/template.py scripts/adapters/myplatform.py
# 改 name / display / supports / 各 solve_* 方法，然后：
python scripts/solve.py --platform myplatform --op ...
```

`BaseSolver` 接口契约：类属性 `name`（小写唯一）、`display`、`supports={token,image,slide,click,rotate}`、`secret_fields`；方法 `solve_token / solve_image / solve_slide / solve_click / solve_rotate`；通过 `self.secret(field, env_name)` 读 `config.json` 段或环境变量；复用 `post_json / post_form / img_to_b64` 辅助函数。

### skill 去了解「新平台 API」并生成适配器

当用户说「接一下 XX 打码平台，文档在 https://…」时，执行**学习工作流**：

1. **调研**：用 WebFetch / WebSearch 抓该平台文档/首页，提取——base URL、鉴权方式（key 字段名/环境变量名）、endpoint（create/result/image/slide 等）、请求/响应字段、支持哪些验证码类型、价格。
2. **整理 spec**：把提取结果写成一个 spec JSON（字段见 `scripts/learn_platform.py` 顶部注释），至少含 `name / display / base_url / auth / supports / endpoints / notes`。
3. **生成骨架**：`python scripts/learn_platform.py --spec spec.json --write` 产出 `scripts/adapters/<name>.py`，已按 supports 填好方法签名、endpoint 常量，并保留「调研备注 + TODO 解析」供补全。
4. **补解析**：打开生成的 `.py`，按该平台真实返回结构补全每个 `solve_*` 的取值逻辑（这一步通常需 LLM/用户结合真实返回微调）。
5. **配置密钥**：在 `scripts/config.json` 加 `<name>` 段（或走 `setup.py`），填入 `secret_fields` 对应的密钥；**绝不进对话**。
6. **冒烟测试**：`python scripts/solve.py --platform <name> --op image --image cap.png`（用该平台支持的便宜类型先跑通），再视情况跑 token/slide。

> 已有完整接入文档的平台（含三家内置）见 `references/external-platforms.md` 的「已整理」清单；未知平台一律走上面的学习工作流。

## 安全与合规

- **密钥只在本地 `config.json`**：用 `scripts/setup.py` 写入（不回显、不入库、不进对话）；只用 `config.example.json` 占位。外接平台的密钥同样只写 `config.json`，严禁在对话里粘贴 clientKey / 密码 / token。
- 平台账号是付费资源，报错/重试要有退避，避免刷爆额度或触发冻结（JFBYM 明确说乱报错可能冻号）。
- 自动化点击（R2）遵守目标站点 robots/服务条款；本 skill 用于你有权爬取的私有/自有业务或授权测试。
- 外接第三方平台时，确认其服务条款允许你的使用场景；不要把敏感业务数据交给不信任的平台。

关键差异速记：

- **YesCaptcha**：2captcha 兼容，`clientKey` 鉴权，`createTask` → `getTaskResult` 轮询。强 token，无滑块。有国际/中国双节点。
- **BingTop**：自研 API，`username`+`password` 鉴权，`captchaType` 整数类型 ID + `captchaData` base64，阻塞式单次返回（不轮询）。类型极全，价格最低。
- **JFBYM**：`token` 鉴权，图片类走 `customApi`（image/slide_image+background_image/extra），token 类走 `funnelApi` 异步两步走（先取 `captchaId`+`recordId`，再 `funnelApiResult` 取令牌）。2captcha 风格，类型最均衡。

## 失败模式

| 现象 | 处理 |
|---|---|
| 类型识别不出 | 向用户要验证码截图或 JS/网络样本，不要硬猜 |
| config.json 不存在 / 密钥未填 | 先 `python preflight.py` 诊断；引导 `preflight.py --init` + `setup.py`；**停步不调平台** |
| 用户没有任何打码平台账号 | 说明可走 R3；引导 MCP/Chrome 配置，不要求密钥 |
| 平台返回坐标但浏览器点击仍失败 | 先看坐标是否相对原图/显示图、缩放系数、是否需同轮 session |
| 易盾滑块拖拽偏右/偏左 | 调 `yidun_slide.py` 的 `SLIDE_CALIB_BIAS`；确认轨道用 `.yidun_control` 非 `.yidun_slider`；见 `yidun-r2-automation.md` |
| YesCaptcha 调滑块 | 不可能——它没有滑块类，改走 BingTop/JFBYM 双图滑块或 R3 |
| JFBYM `funnelApi` 返回 10004/10009 | 触发限流，sleep 几秒后重试，直到 10001 成功或 10010 失败 |
| BingTop `code != 0` | 看 message；区分 `captcha type error`（换 type）与 `请稍后再试`（限流退避）；图片 base64 不要带 `data:image/...;base64,` 前缀 |
| BingTop 图标点选双图 | `captchaData`=背景 PNG 截图，`subCaptchaData`=提示图；账号未开通 `13202` 时用 `13242` 备选；见 `icon-click-r2.md` |
| 协议路线（R3）`forbidden`/`param decrypt error` | 移交 `captcha-slide-reverse` 对应分支排查同轮参数 |

## 交付标准

1. 明确验证码类型与厂商，不混用字段与算法。
2. 给用户至少两条可选路线（除非类型客观上只有一条），并标注成本/稳定性/浏览器依赖/账号暴露。
3. 调平台时严格按 `references/platforms.md` 字段，密钥走配置不硬编码。
4. R3 路线移交 `captcha-slide-reverse` 并说明衔接点，不直接重写其逆向细节。
5. 失败时打印关键中间值（平台返回 code/message、taskId/captchaId、坐标/距离/令牌前缀）。
