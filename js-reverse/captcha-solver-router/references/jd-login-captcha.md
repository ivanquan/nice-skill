# 京东 PC 登录 JCAP 验证码（jd-login-captcha）

> 实测页面：`https://passport.jd.com/new/login.aspx`  
> 引擎：`scripts/jd_login_captcha.py` + `scripts/captcha_type_detect.py` + `scripts/bingtop_types.py`

## 1. 题型与冰拓 captchaType（须按识别类别分发）

**官方文档**：[冰拓类型说明](https://www.bingtop.com/type/)  
**常量表**：`scripts/bingtop_types.py` → `resolve_captcha_type(category)`

| 识别类别 | 文案/DOM 信号 | BingTop captchaType | 引擎 |
|---|---|---|---|
| **rotate** 旋转 | `请拖动滑块使图片为正`、`使图片为正` | **11201**（备选 **1120**） | `rotate_captcha.py` |
| **track** 轨迹绘制 | `轨迹`、`绘制`、`按图中` | **3002** | `track_draw.py` |
| **slide** 滑动拼图 | `.JDJRV-smallimg` + 手柄、拼图文案 | **1310**（备选 **1318**） | `jd_jcap_slide.py` |

**禁止使用的历史误用 ID**（官网不存在）：`11203`、`112013`、`30013`、`13563`、`13102`、`13182`。

识别为 `rotate` 时**不得**传轨迹 `3002`；由 `resolve_captcha_type()` 按 `category` 自动选择。

## 2. 新版浮层 DOM（2026 实测，MCP 校准）

旧版 `#slideAuthCode` / `.JDJRV-*` 在登录页常为 **0×0 空壳**；真实浮层为：

| 用途 | 选择器 |
|---|---|
| 浮层遮罩 | `.captcha_drop` |
| 浮层主体 | `#captcha_modal.captcha_modal_pc` |
| 提示文案 | `#local_tip`（旋转：「请拖动滑块使图片为正」） |
| 旋转主图 | `.captcha_body .slot-content img` |
| 旋转手柄 | `#slider-div` |
| 滑轨 | `.captcha_footer .drag-box`（宽约 290px，手柄约 48px） |
| 刷新 | `.jcap_refresh` / `#refreshPng` |

**默认 widget**（`captcha_type_detect.DEFAULT_WIDGET`）：

```text
#captcha_modal, .captcha_modal_pc, .captcha_drop, #slideAuthCode, .slide-authCode-wraper
```

浮层可见判定：`jd_captcha_overlay_visible()` 优先认 `#captcha_modal` 可见 +「安全验证」等文案。

## 3. 类型识别（captcha_type_detect）

优先级：**轨迹文案 > 旋转文案 > 滑块 DOM**。

旋转关键文案：`使图片为正`（含「滑块」字样仍是旋转，不是 slide）。

`page.evaluate` 只传 **一个 payload 对象**（Playwright 限制），见 `captcha_type_detect._DETECT_JS`。

输出字段含 `bingtop_captcha_type`，供分发与日志。

## 4. 旋转拖拽要点（rotate_captcha.py）

常见失败原因与修复：

| 问题 | 修复 |
|---|---|
| 用整条轨道宽 290px 换算 | 用 **有效行程** `effectiveW = trackW - handleW`（约 242px） |
| 从手柄当前位置累加偏移 | **从滑轨起点拖到目标绝对位置** |
| 重试时滑块停在中间 | 失败后点 **刷新** 再识图（`refresh_rotate_captcha`） |
| `human_drag` 未触发页面监听 | 改用 **`human_slide_drag(accurate=True)`** |

日志示例：

```text
[rotate-captcha] 拖拽 angle=91.0° offset=61.1px effective=242 (335,340)→(396,340)
```

成功判定：见过浮层后 `#captcha_modal` 消失（`is_jd_captcha_success(..., challenge_seen=True)`）。

## 5. CLI 与项目内 Demo

```bash
# 项目内薄封装（推荐）
python jd_login_test.py
# 或显式凭据
python jd_login_test.py --login-user USER --login-pass PASS

# 直接调 skill 引擎
python scripts/automate.py --backend playwright --op jd-login-captcha \
  --target-url "https://passport.jd.com/new/login.aspx?ReturnUrl=..." \
  --platform bingtop \
  --widget-selector "#captcha_modal, .captcha_modal_pc, .captcha_drop" \
  --track-captcha-type 3002 --rotate-captcha-type 11201 --slide-captcha-type 1310 \
  --jd-login-user USER --jd-login-pass PASS
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--track-captcha-type` | 3002 | 仅 track 类别使用 |
| `--rotate-captcha-type` | 11201 | 仅 rotate 类别使用 |
| `--slide-captcha-type` | 1310 | 仅 slide 类别使用 |
| `--no-auto-trigger` | — | 手动触发浮层后只识别+求解 |

环境变量：`JD_LOGIN_USER` / `JD_LOGIN_PASS`。

## 6. 调试

- `BINGTOP_DEBUG=1`：打印冰拓请求/响应（`adapters/bingtop.py`）
- 废弃 type 会打印纠正提示（`bingtop_types.warn_deprecated_type`）
- 浮层未出现：检查登录点击、`panel_seen`、等待 40s 内 `page_text`
- 旋转拖完未过：看 `offset/effective` 坐标；可试 `--rotate-captcha-type 1120`

## 7. 相关脚本

| 文件 | 作用 |
|---|---|
| `bingtop_types.py` | 官方 captchaType 常量 + 按类别解析 |
| `captcha_type_detect.py` | 文案+DOM 识别 track/rotate/slide |
| `jd_login_captcha.py` | 登录触发 → 等浮层 → 识别 → 分发 |
| `jd_jcap_slide.py` | 滑块 + 浮层检测 + 登录填表 |
| `rotate_captcha.py` | 旋转 R2（几何测量 + 刷新重试） |
| `track_draw.py` | 轨迹 R2（3002） |
