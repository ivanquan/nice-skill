# 网易易盾滑动拼图 — R2 自动化（yidun-slide）

本文件描述 `captcha-solver-router` 内置的易盾滑块 **R2 自动化点击过** 流程。协议过（R3）仍见 `captcha-slide-reverse/references/yidun-workflow.md`。

## 适用场景

| 信号 | 示例 |
|---|---|
| Demo 页 | `https://dun.163.com/trial/jigsaw` |
| 网络 | `c.dun.163.com/api/v3/get` 返回 `bg` + `front` + `token` |
| DOM | `.yidun--jigsaw`、`.yidun_slider`、`.yidun_control`、`.yidun_bgimg` |

**路线**：R2 — BingTop/JFBYM 双图识别距离 + Playwright/CloakBrowser 拟人拖拽。**不用 ddddocr**。

## 核心脚本

| 文件 | 作用 |
|---|---|
| `scripts/yidun_slide.py` | 触发面板 → 抓图 → 平台识别 → 距离换算 → 拟人拖拽 |
| `scripts/yidun_click.py` | 共用：`find_yidun_widget`、`install_yidun_front_hook`、`get_yidun_slide_urls_from_network`、`is_yidun_success` |
| `scripts/browser_stealth.py` | `human_slide_drag(accurate=True)` 拟人轨迹 + 精确落点 |
| `scripts/automate.py` | CLI 入口 `--op yidun-slide` |

## CLI 用法

```bash
# 易盾官方 Demo（普通版 / 默认 widget）
python scripts/automate.py --backend playwright --op yidun-slide \
  --target-url "https://dun.163.com/trial/jigsaw" \
  --platform bingtop \
  --yidun-widget-selector ".yidun--jigsaw, .yidun" \
  --wait-until networkidle --hold-seconds 10

# Demo：触发式 tab（jigsaw 页 tab 顺序：触发式=1、嵌入式=2、弹出式=3）
python scripts/automate.py --backend playwright --op yidun-slide \
  --target-url "https://dun.163.com/trial/jigsaw" \
  --platform bingtop \
  --pre-click ".tcapt-tabs__tab:nth-child(1)" \
  --yidun-widget-selector ".yidun--float"

# Demo：嵌入式 tab
python scripts/automate.py --backend playwright --op yidun-slide \
  --target-url "https://dun.163.com/trial/jigsaw" \
  --platform bingtop \
  --pre-click ".tcapt-tabs__tab:nth-child(2)" \
  --yidun-widget-selector ".yidun--inline"
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `--platform bingtop` | 推荐；滑块双图默认 `captchaType=1310` |
| `--click-captcha-type 1310` | 覆盖冰拓类型（备选 `1318`） |
| `--yidun-widget-selector` | 指定 widget 根节点（多实例页必填） |
| `--pre-click` | 切换 Demo tab 或弹出浮层前先点 |
| `--no-auto-trigger` | 面板已展开时跳过点击验证条 |
| `--click-max-rounds 3` | 最大重试轮次 |
| `--humanize-factor 1.3` | 拟人节奏倍率 |
| `--no-stealth` | 调试用，关闭反检测（不推荐） |

### 输出 JSON

```json
{
  "ok": true,
  "op": "yidun-slide",
  "platform": "bingtop",
  "slide_rounds": 1,
  "offset": 108,
  "yidun_success": true,
  "verified": true,
  "verify_tip": "yidun slide passed"
}
```

## 流程（solve_yidun_slide）

1. **反检测**：`install_yidun_front_hook` 监听 `get` 响应缓存 `bg`/`front` URL。
2. **触发**：`trigger_yidun` 点击 `.yidun_control`（拟人 `human_click_at`）。
3. **等图**：优先网络 URL 下载 bg+slice；兜底 DOM 截图。
4. **识别**：`bingtop.solve_slide(bg, slice, captchaType=1310)` 得缺口 X（bg 原图像素）。
5. **换算**：`calc_slide_drag_distance`（见下节）。
6. **拖拽**：`human_slide_drag(accurate=True)` 变速 + Y 抖动 + 精确落点。
7. **成功**：`is_yidun_success` 检测 `.yidun--success` / 验证成功文案。

## 距离换算算法（calc_slide_drag_distance）

打码平台（冰拓 1310）返回值为 **拼图块左缘在 bg 原图上的目标 X**（像素，常见 bg 宽 320）。

```
bg_travel   = bg_w - slice_w      # 背景上拼图可移动区间（例 320-60=260）
track_travel = track_w - handle_w  # 轨道上可拖拽区间（例 320-40=280，用 .yidun_control 非 .yidun_slider）

drag_base = gap_x × track_travel / bg_travel
drag      = drag_base - calib(3~5.5px) + jitter(±0.5px)
```

**要点**：

- **轨道宽度**取 `.yidun_control`（~320px），**勿**取 `.yidun_slider` 手柄宽（~40px），否则距离会缩小 8 倍。
- **拼图块宽度** `slice_w` 参与 `bg_travel` 分母，避免重复放大。
- **标定偏置** `SLIDE_CALIB_BIAS = (3.0, 5.5)`：修正实测系统性偏右；仍偏右则加大，偏左则减小（改 `yidun_slide.py` 顶部常量）。
- **不用 ddddocr**；R2 距离只走第三方打码。

几何读取：`measure_yidun_slide_geometry` 从 DOM 取 `bgNaturalW`、`sliceNaturalW`、`trackW`（control）、`handleW`（slider）。

## 拟人拖拽（human_slide_drag）

验证码场景使用 `accurate=True`：

| 特性 | 说明 |
|---|---|
| 变速 | 三次缓动 ease-in-out（起步慢、中段快、收尾慢） |
| Y 抖动 | 中段 ±2.8px，起止稳定 |
| 无 X 抖动 | 避免落点偏右 |
| 无末端过冲 | 验证码禁用 overshoot |
| 精确吸附 | 松手前 `mouse.move(x1, y0)` 消除累积偏差 |

通用滑块 `--op slide` 使用同轨迹（无 `accurate` 时可带过冲，更像真人）。

## Demo 页 tab 与 widget 对照

**jigsaw 页**（`/trial/jigsaw`）与 **picture-click 页** tab 序号不同：

| 模式 | pre-click | widget |
|---|---|---|
| 触发式 | `.tcapt-tabs__tab:nth-child(1)` | `.yidun--float` |
| 嵌入式 | `.tcapt-tabs__tab:nth-child(2)` | `.yidun--inline` |
| 普通版（默认） | 无 | `.yidun--jigsaw, .yidun` |

## 打码平台

| 平台 | captchaType | 入参 |
|---|---|---|
| BingTop | `1310`（默认，备选 `1318`） | `captchaData`=bg，`subCaptchaData`=slice |
| JFBYM | `20111` | `background_image` + `slide_image` |

详见 `references/platforms.md` §2.3.2。

## 排查

| 现象 | 处理 |
|---|---|
| 找不到 widget | 检查 `--yidun-widget-selector` 与 `--pre-click` tab |
| 拖拽偏右 3~5px | 调大 `SLIDE_CALIB_BIAS` 上界 |
| 拖拽偏左 | 调小 `SLIDE_CALIB_BIAS` 或改为 `(1.0, 3.0)` |
| 用 DOM 截图非网络图 | 等 `wait_yidun_network_images`；检查 hook 是否早于页面加载 |
| 识别 type error | 换 BingTop 备选类型 `1318` |
| 行为风控失败 | 换 `--backend cloak`；确认本机 Chrome + stealth 已开 |

## 与 captcha-slide-reverse 衔接

- **R2（本文件）**：省事，依赖打码平台，适合 Demo/业务快速验证。
- **R3**：`api/v3/get` → OCR → 轨迹 `data` → `api/v3/check`，零边际成本，见 `yidun-workflow.md`。
