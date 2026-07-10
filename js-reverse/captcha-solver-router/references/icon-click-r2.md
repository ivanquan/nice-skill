# 通用图标点选 R2 自动化（icon-click）

厂商无关的图标点选流程：`--op icon-click` + 可插拔 `--click-provider`。易盾仅为内置 Provider 之一。

## 架构

```
icon_click.py          # 通用流程：触发 → 抓图 → 平台识别 → 拟人点击
click_providers/
  __init__.py          # Provider 注册与 auto 解析
  yidun.py             # 易盾 DOM：.yidun--icon_point + .yidun_tips__img
```

新增厂商时：实现 Provider 类并注册到 `PROVIDER_REGISTRY`，无需改 `icon_click.py` 主流程。

## Provider 接口（约定方法）

| 方法 | 作用 |
|---|---|
| `prepare()` | 网络 hook 等前置 |
| `trigger(pacer)` | 展开验证码面板 |
| `panel_visible()` | 面板是否可见 |
| `wait_ready(pacer)` | 等待背景图+提示图就绪 |
| `read_instruction()` | 题面文字 |
| `read_hint_b64()` | 图标提示图 base64 |
| `capture_bg_b64()` | 背景图 (b64, selector, natural_wh) |
| `expected_click_count(hint)` | 预估点击次数 |
| `click_points(...)` | 拟人点击坐标 |
| `is_success()` | 验证是否通过 |
| `reload(pacer)` | 刷新挑战 |

## CLI

```bash
# 易盾 Demo（自动或显式 provider）
python scripts/automate.py --backend playwright --op icon-click \
  --target-url "https://dun.163.com/trial/icon-click" \
  --platform bingtop \
  --click-provider yidun \
  --widget-selector ".yidun--icon_point, .yidun" \
  --wait-until networkidle

# 嵌入式 tab
python scripts/automate.py --backend playwright --op icon-click \
  --target-url "https://dun.163.com/trial/icon-click" \
  --platform bingtop \
  --pre-click ".tcapt-tabs__tab:nth-child(2)" \
  --widget-selector ".yidun--inline"
```

## 打码平台

| 平台 | 默认 captchaType | 入参 |
|---|---|---|
| BingTop | `13202`（备选 13134/13242） | `captchaData`=背景图，`subCaptchaData`=图标提示图 |
| JFBYM | `30009` | `image` + 可选 `extra` |

图标点选与文字点选区别：题面为**图标提示图**（非汉字 extra），走双图识别。

## 输出 JSON

```json
{
  "ok": true,
  "op": "icon-click",
  "platform": "bingtop",
  "click_provider": "yidun",
  "click_rounds": 1,
  "instruction": "请依次点击...",
  "points": [[120, 80], [200, 150]],
  "captcha_success": true,
  "yidun_success": true
}
```

## 与 yidun-click 的关系

| op | 类型 | 题面 | BingTop 类型 |
|---|---|---|---|
| `yidun-click` | 文字点选 | 汉字 extra | 13152 |
| `icon-click` | 图标点选 | 图标提示图 | 13202 |

二者共用 `yidun_click.py` 的点击/反检测工具，但 **op 与 Provider 分离**，便于接入腾讯/极验等图标点选。

## Demo 页 tab（icon-click）

| 模式 | pre-click | widget |
|---|---|---|
| 触发式 | `.tcapt-tabs__tab:nth-child(1)` | `.yidun--float` |
| 嵌入式 | `.tcapt-tabs__tab:nth-child(2)` | `.yidun--inline` |
| 默认 | 无 | `.yidun--icon_point, .yidun` |
