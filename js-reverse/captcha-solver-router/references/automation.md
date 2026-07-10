# R2 自动化驱动选型手册（反爬浏览器）

R2（自动化点击过）的核心是：**平台/协议给出坐标、距离、角度或答案后，用反爬浏览器驱动拟人地把验证码过掉**。本 skill 全程 **Python 技术栈**，R2 引擎统一封装在 `scripts/automate.py`，支持下列后端，按场景切换。

---

## 1. 可选驱动一览

| 驱动 | 内核 | 反检测强度 | 安装 | 何时用 |
|---|---|---|---|---|
| **CloakBrowser** | 源码级 C++ 补丁 Chromium（66 处指纹补丁） | ★★★★★ 最强 | `pip install cloakbrowser` | 强反爬站点（Cloudflare/DataDome/Akamai/reCAPTCHA v3 企业版）；对 Playwright 零配置替换；返回标准 Playwright `Browser`，原 Playwright 代码几乎不改 |
| **DrissionPage（DP）** | Chromium + 内置 Session | ★★★☆☆ 够用 | `pip install DrissionPage` | 轻量、省事、中文友好；滑块/点选单页任务；自带 `excludeSwitches` 类反检测，比原生 Selenium 难识别 |
| **Playwright（原生）** | Chromium/Firefox/WebKit | ★★☆☆☆ 原生易被识别 | `pip install playwright && playwright install chromium` | 需手动叠加 stealth（见 §5）；或仅做内部/低风险目标；生态最全 |
| **Camoufox** | Firefox 反向定制（Playwright 接入） | ★★★★☆ 强（Firefox 指纹天然难打） | `pip install camoufox && camoufox fetch` | 偏好 Firefox 指纹、想绕 Chromium 专属检测时 |
| **nodriver / undetected-chromedriver** | CDP 直连 Chrome | ★★★☆☆ | `pip install nodriver` | 纯 token 类、无需复杂交互、要 async 时 |

> **选型口诀**：强反爬 → CloakBrowser；轻量单页滑块/点选 → DrissionPage（DP）；要 Firefox 指纹 → Camoufox；只用 Playwright 生态且目标不强 → 原生 Playwright + stealth。

---

## 2. CloakBrowser（推荐默认强反爬）

源码级隐形 Chromium，不是 JS 注入、不是配置篡改，而是把指纹在 C++ 层改成真实浏览器形态。对 Playwright **drop-in 替换**：

```bash
pip install cloakbrowser
# 仅需装系统依赖（二进制首次运行自动下载 ~200MB）
playwright install-deps chromium
# 可选 GeoIP（按代理 IP 自动匹配时区/语言）
pip install cloakbrowser[geoip]
```

```python
from cloakbrowser import launch

# 无头（默认隐身配置）
browser = launch()
# 有头可见 + 拟人化鼠标/键盘/滚动（贝塞尔移动、逐字符输入）
browser = launch(headless=False, humanize=True)
# 带代理
browser = launch(proxy="http://user:pass@proxy:8080")
# Pro 二进制 / 固定指纹身份
browser = launch(license_key="cb_xxx")          # 或环境变量 CLOAKBROWSER_LICENSE_KEY
browser = launch(fingerprint="seed_string")     # 固定身份（同身份复用）

page = browser.new_page()
page.goto("https://target.example/captcha")
# 以下完全复用 Playwright API（page.locator / page.mouse / page.evaluate ...）
page.locator("#slider").drag_to?  # 见 §4 的拟人拖拽
```

> `humanize=True` 时**必须用 `page.locator().click()` / `page.click(selector)`**，不要用 `element_handle` 直接操作（会绕过补丁）。

---

## 3. DrissionPage（DP，轻量首选）

融合 Session + Chromium 的轻量库，自带反检测（默认 `excludeSwitches`、关闭 `AutomationControlled` 等标志），语法简洁。

```bash
pip install DrissionPage
```

```python
from DrissionPage import ChromiumPage, ChromiumOptions

co = ChromiumOptions()
co.headless(True)                       # 无头
co.set_argument('--disable-blink-features=AutomationControlled')
co.set_proxy("http://user:pass@proxy:8080")
page = ChromiumPage(co)

page.get("https://target.example/captcha")
slider = page.ele("#slider")           # 支持 #id / .class / @attr=value / xpath
# 直接按偏移拖拽（DP 内部做缓动）
slider.drag(120, 0, duration=1.2)      # 向右 120px，约 1.2s
# 或事件链（更可控）
page.actions.hold(slider).move(120, 0).release()
# 点选：给定相对验证码图片的坐标
cap = page.ele("#captcha-img")
cap.click.at((120, 80))                # DrissionPage 的点击定位语法
```

> DP 适合单页、轻交互；若要精确贝塞尔拟人轨迹，用 CloakBrowser/Playwright 后端（`automate.py --backend cloak`）。

---

## 4. 拟人化交互模板（统一在 automate.py 实现）

R2 引擎 `scripts/automate.py` 已内置下列拟人逻辑，调用方无需关心后端差异：

### 4.1 滑块拖拽（slide / yidun-slide）
给定**像素距离** `offset`（来自平台双图滑块或 captcha-slide-reverse 协议）：
- 取滑块中心为起点；
- **`human_slide_drag`**：三次缓动变速 + Y 轴抖动 + 随机微停顿；验证码场景 `accurate=True` 时禁用 X 抖动与末端过冲，松手前精确吸附落点；
- 通用 `--op slide` 可带过冲回正，更像真人；
- 全程约 1.2–2.5s。

**易盾滑动拼图（`--op yidun-slide`）** 额外逻辑见 `references/yidun-r2-automation.md`：
- 冰拓 1310 识别缺口 X → `calc_slide_drag_distance`（bg/slice/track/handle 几何换算 + `SLIDE_CALIB_BIAS` 标定）；
- 轨道宽度取 `.yidun_control`（~320px），勿用手柄 `.yidun_slider`（~40px）；
- 不用 ddddocr。

### 4.2 点选（click）
给定**相对验证码图片的像素坐标列表**（来自平台）：
- 取图片 `bounding_box`，把相对坐标 + 图片左上角偏移 → 页面绝对坐标；
- 逐点：移动到目标 → 短停 → 点击 → 间隔 0.2–0.5s（避免机器节奏）。

### 4.3 旋转（rotate / rotate-captcha）

给定**角度** `angle`：
- 按**有效行程**换算水平像素：`px = (track_width - handle_width) * angle / full_angle`（京东新版滑轨约 290px，手柄约 48px → effective ≈ 242px）；
- 从滑轨**起点**拖到目标绝对位置，使用 `human_slide_drag(accurate=True)`；
- 失败后刷新验证码再重试（`rotate_captcha.py`）。

京东登录等多题型见 `references/jd-login-captcha.md`。

### 4.4 token 注入（token）
R1 平台解出令牌后的「浏览器内回填」：
- 把 `token` 写入 `g-recaptcha-response` / `h-captcha-response` / `cf-turnstile-response` 等隐藏 textarea（用 value setter + dispatch input/change 事件，绕过框架只读劫持）；
- 若小部件带 `data-callback`，触发该回调；
- 现代 reCAPTCHA v3 / 企业版多数走 iframe + 业务侧 HTTP 提交，更推荐 R1 直接在业务 POST 里带 `gRecaptchaResponse`，而非浏览器注入——见 SKILL.md 第 5 步说明。

### 4.5 网易易盾与通用点选（yidun-click / yidun-slide / icon-click）

内置 `--op`，无需手写 selector。易盾仅为 Provider 之一。

```bash
# 图标点选（通用，易盾 Demo）
python scripts/automate.py --backend playwright --op icon-click \
  --target-url "https://dun.163.com/trial/icon-click" --platform bingtop \
  --click-provider yidun --widget-selector ".yidun--icon_point"

# 文字点选
python scripts/automate.py --backend playwright --op yidun-click \
  --target-url "https://dun.163.com/trial/picture-click" --platform bingtop
```

| op | 类型 | BingTop | 文档 |
|---|---|---|---|
| `icon-click` | 图标点选（Provider 可插拔） | `13202` | `icon-click-r2.md` |
| `yidun-click` | 易盾文字点选 | `13152` | 同上 |
| `yidun-slide` | 易盾滑动拼图 | `1310` | `yidun-r2-automation.md` |
| `jd-login-captcha` | 京东登录（旋转/轨迹/滑块自动识别） | 按题型 `11201`/`3002`/`1310` | `jd-login-captcha.md` |
| `jd-jcap-slide` | 京东 JCAP 滑动拼图 | `1310` | `jd-login-captcha.md` |
| `track` | 轨迹绘制 | `3002` | `jd-login-captcha.md` |
| `rotate-captcha` | 通用旋转 R2 | `11201` | `jd-login-captcha.md` |

默认启用 `browser_stealth.py` 反检测；Playwright 后端建议配置本机 Chrome（`config.json` → `automation.chrome_executable`）。

---

## 5. 原生 Playwright 的 stealth 补充

原生 Playwright 默认会被 `navigator.webdriver`、`cdc_` 变量、`window.chrome` 缺失等识别。补强方式：

**推荐**：`scripts/automate.py` 已内置 `browser_stealth.py`，默认通过 `BrowserContext` 注入 UA/viewport/locale 与 init script；CLI 默认开启，可用 `--no-stealth` 关闭（调试用）。

```python
from browser_stealth import create_stealth_context, CHROME_STEALTH_LAUNCH_ARGS

browser = p.chromium.launch(headless=True, args=CHROME_STEALTH_LAUNCH_ARGS)
ctx = create_stealth_context(browser, backend="playwright")
page = ctx.new_page()
```

手写示例（未走 automate 时）：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True,
        args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="zh-CN",
    )
    page = context.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    """)
    # ... 交互同 §4
```

> 若目标强反爬，**直接用 CloakBrowser 替代上面整段**（`--backend cloak`），省事且更稳。验证码 R2 场景默认优先 CloakBrowser。

### 5.1 本机 Chrome 路径（Playwright 后端）

Playwright **不会**写死任何本机路径。请在 `scripts/config.json` 配置：

```json
"automation": {
  "chrome_executable": "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "chrome_debug_port": 9222
}
```

首次配置：`python scripts/setup.py` → 选择配置 Chrome 路径。  
也可设环境变量 `CHROME_EXECUTABLE`，或 CLI `--chrome-path`。未配置时使用 Playwright 自带 Chromium。

---

## 6. 调 R2 引擎（CLI）

```bash
# 滑块：CloakBrowser 后端，给定像素偏移
python scripts/automate.py --backend cloak --op slide \
  --target-url "https://target/captcha" --slider-selector "#slider" --offset 128

# 点选：DrissionPage 后端，给定相对图片坐标
python scripts/automate.py --backend drissionpage --op click \
  --target-url "https://target/captcha" --captcha-img-selector "#captcha" \
  --points "[[120,80],[200,150],[90,220]]"

# 旋转：Playwright 后端，给定角度
python scripts/automate.py --backend playwright --op rotate \
  --target-url "https://target/captcha" --handle-selector "#rotate-handle" --angle 45

# token：CloakBrowser 后端，先调 solve.py 解出令牌再注入页面
python scripts/automate.py --backend cloak --op token \
  --target-url "https://target/captcha" --platform yescaptcha \
  --sitekey 6Le-xxx --url "https://target/captcha"

# 网易易盾滑动拼图
python scripts/automate.py --backend playwright --op yidun-slide \
  --target-url "https://dun.163.com/trial/jigsaw" --platform bingtop \
  --yidun-widget-selector ".yidun--jigsaw, .yidun"

# 京东登录验证码（自动识别旋转/轨迹/滑块）
python scripts/automate.py --backend playwright --op jd-login-captcha \
  --target-url "https://passport.jd.com/new/login.aspx" --platform bingtop \
  --widget-selector "#captcha_modal, .captcha_modal_pc, .captcha_drop" \
  --track-captcha-type 3002 --rotate-captcha-type 11201 \
  --jd-login-user USER --jd-login-pass PASS
```

后端缺包时引擎会给出明确安装提示，不会崩溃。易盾 R2 详见 `references/yidun-r2-automation.md`。详见 `scripts/automate.py` 内 docstring。
