# 打码平台接入手册（YesCaptcha / BingTop / JFBYM）

本文件是 `captcha-solver-router` 的平台知识库。接 API 时**严格照字段名**，不要自创参数。三家都已在 `scripts/solve.py` 封装，直接调脚本即可；此处留作字段核对与排错。

---

## 1. YesCaptcha（token 类首选）

2captcha 兼容协议。`clientKey` 鉴权，`createTask` 建任务 → `getTaskResult` 轮询拿结果。

### 1.1 节点与地址
- 国际节点：`https://api.yescaptcha.com`
- 中国节点：`https://cn.yescaptcha.com`
- `createTask`：`POST {node}/createTask`，`Content-Type: application/json`
- `getTaskResult`：`POST {node}/getTaskResult`，`Content-Type: application/json`

### 1.2 建任务（createTask）
请求体：
```json
{
  "clientKey": "你的clientKey",
  "task": {
    "type": "NoCaptchaTaskProxyless",
    "websiteURL": "https://www.google.com/recaptcha/api2/demo",
    "websiteKey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
  }
}
```
响应：
```json
{ "errorId": 0, "errorCode": "", "errorDescription": null, "taskId": "7cf17d74-..." }
```

### 1.3 取结果（getTaskResult，轮询）
请求体：
```json
{ "clientKey": "你的clientKey", "taskId": "7cf17d74-..." }
```
响应（`status: "ready"` 时取 `solution`）：
```json
{
  "errorId": 0,
  "status": "ready",
  "solution": { "gRecaptchaResponse": "03AGdBq27gCf7UkBFO7..." }
}
```

### 1.4 常用 task.type（本 skill 涉及）
| 类型 | type 值 | 返回 | 点数 |
|---|---|---|---|
| 图片不定长英数 | `ImageToTextTask` | 答案字符串（body=base64） | 2–15 |
| reCAPTCHA v2 | `NoCaptchaTaskProxyless` / `RecaptchaV2TaskProxyless` | `gRecaptchaResponse` | 15–20 |
| reCAPTCHA v3 | `RecaptchaV3TaskProxyless`（可加 `minScore`/`version`） | `gRecaptchaResponse` | 20–30 |
| hCaptcha | `HCaptchaTaskProxyless` | `hCaptchaResponse` | 30 |
| Cloudflare Turnstile | `TurnstileTaskProxyless` | `token` | 25–30 |
| Cloudflare 5s 盾 | `CloudFlareTaskS2` | cookies | 25（质量差，不推荐） |

> 汇率：1 元 = 1000 POINTS。无滑块类——滑块必须走 BingTop/JFBYM 或 R3 协议。

### 1.5 Python SDK（可选）
```bash
pip install yescaptcha
```
```python
from yescaptcha.task import NoCaptchaTaskProxyless
from yescaptcha.client import Client, Region
client = Client(client_key="你的clientKey", region=Region.CHINA)  # 中国节点
task = NoCaptchaTaskProxyless(website_key="6Le-...", website_url="https://...")
job = client.create_task(task)
print(job.get_solution())   # 自动轮询
```

---

## 2. BingTop 冰拓（图片/滑块/旋转/点选首选，价格最低）

自研 API。`username`+`password` 鉴权，**阻塞式单次返回（不轮询）**，建议超时 40s。

### 2.1 地址与格式
- 识别：`POST https://www.bingtop.com/ocr/upload/`（兼容 http）
- `Content-Type: application/x-www-form-urlencoded`，返回 JSON
- 报错：`POST http://www.bingtop.com/ocr/report/`
- 查点：`POST http://www.bingtop.com/ocr/check_points/`

### 2.2 识别请求
| 参数 | 必填 | 说明 |
|---|---|---|
| `username` | 是 | 登录用户名 |
| `password` | 是 | 登录密码 |
| `captchaType` | 是 | 整数类型 ID（见下） |
| `captchaData` | 是 | 图片 base64（**不带** `data:image/...;base64,` 前缀） |
| `subCaptchaData` | 否 | 第二张图 base64（部分类型需要，如双图滑块/旋转） |

响应：
```json
{ "code": 0, "message": "", "data": { "captchaId": "1000-158201918112812", "recognition": "RESULT" } }
```
`code != 0` 看 `message`；`recognition` 即答案（滑块为 x 或 x,y，旋转为角度，点选为坐标）。

### 2.3 本 skill 常用类型 ID（候选，非固定）

> **不要写死类型 ID。** 冰拓 `captchaType` 随账号开通范围、图片形态而异；须结合[冰拓官方类型说明](http://www.bingtop.com/ocr/upload/)与抓包样本试跑选定。`code != 0` 且提示 type 错误时换候选类型，勿盲猜。

| 用途 | captchaType（候选） | 说明 |
|---|---|---|
| 字符 1–4 位 | `10001` | 英数/纯英/纯数 |
| 字符 1–8 位 | `10011` | |
| 汉字通用 | `11056` | |
| 极验 GT3 双图滑块 | `1310` / `1318` | **须先还原乱序 bg**（`gt3_restore.py` 或 `--gt3-restore`）；`captchaData`=背景图，`subCaptchaData`=滑块；返回常为 `x,y` |
| 单图滑块（返回 x） | `1318` | 普通单图缺口（非 GT3 乱序图） |
| 双图滑块（返回 x 或 x,y） | `1310` | 京东/极验双图滑块常用 |
| 多空缺滑块 | `13162` / `13262` | 主图+滑块图（subCaptchaData） |
| 通用坐标点选 | `13202` / `13134` | 返回点击坐标 |
| 图标点选（双图：背景+提示图） | `13202` / `13134` | `captchaData`=背景，`subCaptchaData`=图标提示图；见 `icon-click-r2.md` |
| 文字点选 | `13242`（传 subCaptchaData 标题或 extra） | |
| 单图旋转 | `11201` / `1120` | 返回角度；**勿用** `11203`/`112013`（不存在） |
| 双图旋转 | `11212` | 传一张，返回角度 |
| 内旋转 | `1123` | 圆图 1–359° |
| 计算题 | `12012` | 返回计算结果 |
| 轨迹类 | `3002` | 返回轨迹坐标序列（京东 JCAP 轨迹绘制）；**勿用** `30013`/`13563` |

#### 2.3.1 极验 GT3 滑块：类型 ID 如何选定

1. **拿图**：用 `scripts/gt3_capture.py` 从 slide `get.php` JSONP 下载 `bg`+`slice`（见 `captcha-slide-reverse` 的 GT3 工作流）；乱序 bg 先 `gt3_restore.py` 还原。
2. **看形态**：双图滑块、背景已还原为 260×160、小图为 slice → 在冰拓文档「双图滑块 / 极验」类目中找对应 ID。
3. **试跑**：`python solve.py --platform bingtop --op slide --captcha-type <候选> --image ... --slice ... [--gt3-restore]`；若 `404 captcha type error` 换下一候选。
4. **验证**：识别结果 `x,y` 应落在背景宽度内；与页面显示宽可能有缩放（常见 260 逻辑宽 → 300 显示宽），拖拽 offset 需按目标页 DOM 换算。
5. **R2 优先第三方**：距离识别走 BingTop/JFBYM，**不用**本地 ddddocr（ddddocr 仅 R3 协议还原路线可选）。

#### 2.3.2 网易易盾滑动拼图：类型 ID 与距离换算

1. **拿图**：`yidun-slide` 流程优先从 `api/v3/get` 网络响应缓存 `bg`+`front` URL 下载；兜底 DOM 截图。
2. **识别**：`captchaType=1310`（双图滑块，备选 `1318`）；`captchaData`=背景 `bg`，`subCaptchaData`=拼图块 `front`/`slice`；返回缺口 X（bg 原图像素，常见宽 320）。
3. **换算**（`yidun_slide.calc_slide_drag_distance`，**不用 ddddocr**）：
   ```text
   drag = gap_x × (track_w - handle_w) / (bg_w - slice_w) - calib(3~5.5px)
   ```
   - `track_w` = `.yidun_control` 宽（~320），**勿**用 `.yidun_slider` 手柄宽（~40）。
   - 标定偏置 `SLIDE_CALIB_BIAS` 在 `scripts/yidun_slide.py` 可调。
4. **拖拽**：`human_slide_drag(accurate=True)` — 变速 + Y 抖动 + 精确落点。
5. **CLI**：`python automate.py --op yidun-slide --platform bingtop --target-url https://dun.163.com/trial/jigsaw`
6. 完整 R2 文档：`references/yidun-r2-automation.md`；协议过 R3 见 `captcha-slide-reverse/references/yidun-workflow.md`。

#### 2.3.3 京东 PC 登录 JCAP：类型 ID 与 DOM

1. **浮层**：新版以 `#captcha_modal.captcha_modal_pc` 为准；`#slideAuthCode` 可能为 0×0 空壳。
2. **识别**：`captcha_type_detect.py` 按文案/DOM 输出 `category`（`rotate`/`track`/`slide`）。
3. **分发 type**（`bingtop_types.resolve_captcha_type`）：
   - 旋转「使图片为正」→ `11201`（备选 `1120`）
   - 轨迹绘制 → `3002`
   - 滑动拼图 → `1310`（备选 `1318`）
4. **旋转拖拽**：有效行程 `trackW - handleW`；绝对坐标 + `human_slide_drag(accurate=True)`；失败刷新重试。
5. **CLI**：`--op jd-login-captcha`；完整说明见 `references/jd-login-captcha.md`。

> 价格低至 ¥0.001/图；类型极全（字符/坐标/滑块/拼图/计算/旋转/轨迹/问答/OCR）。

### 2.4 报错与查点
```text
# 报错（识别错时，2 分钟内有效）
POST http://www.bingtop.com/ocr/report/
username, password, captchaId, captchaType

# 查剩余点数
POST http://www.bingtop.com/ocr/check_points/
username, password  →  data.points
```

---

## 3. JFBYM 云码（类型最均衡，token+滑块+点选通吃）

`token` 鉴权（用户中心密钥）。图片类走 `customApi`，token 类走 `funnelApi` 异步两步。

### 3.1 图片 / 滑块 / 点选（customApi）
- 地址：`POST http://api.jfbym.com/api/YmServer/customApi`
- `Content-Type: application/json` 或 `application/x-www-form-urlencoded`

| 用途 | 参数 |
|---|---|
| 通用图/字符/计算 | `image`(base64), `token`, `type` |
| 滑块缺口 | `slide_image`(小图base64), `background_image`(背景图base64，需先还原), `token`, `type` |
| 点选 | `image`(base64), `token`, `type`, `extra`(需点选的汉字) |

响应（注意 `code` 语义与 funnel 不同）：
```json
{ "code": 10000, "msg": "识别成功", "data": { "code": 0, "data": "答案|像素距离|角度|坐标", "time": "..." } }
```
- 数英/计算：`data`=答案；滑块：`data`=像素距离；旋转：`data`=角度；坐标：`data`=按顺序坐标。

### 3.2 谷歌 reCAPTCHA / hCaptcha（funnelApi，异步两步）
**第 1 步 取凭证**：`POST http://api.jfbym.com/api/YmServer/funnelApi`
| 参数 | 必填 | 说明 |
|---|---|---|
| `token` | 是 | 用户中心密钥 |
| `type` | 是 | `40010`=reCAPTCHA v2，`40011`=reCAPTCHA v3，`50013`=hCaptcha |
| `googlekey` | 是 | 页面 `data-sitekey` |
| `pageurl` | 是 | 验证码所在页地址 |
| `invisible` | 否 | 0/1（默认 1 隐形） |
| `proxy` / `proxytype` | 否 | 代理 |
| `enterprise` | 否 | 是否企业版（默认 0） |
| `action` | 否 | v3 的 action |
| `data-s` / `min_score` | 否 | v2 企业版 / v3 分值 |

返回：`{ "code": 10001, "msg": "请求成功", "data": { "captchaId": "...", "recordId": "..." } }`

**第 2 步 取结果**：`POST http://api.jfbym.com/api/YmServer/funnelApiResult`
| 参数 | 必填 | 说明 |
|---|---|---|
| `token` | 是 | |
| `captchaId` | 是 | 第 1 步返回 |
| `recordId` | 是 | 第 1 步返回 |

`code=10001` 成功并带令牌；`code=10004/10009` 表示限流/准备中，**sleep 几秒重试**，直到 `10001`（成功）或 `10010`（失败）。

### 3.3 余额 / 报错
- 余额：`POST http://api.jfbym.com/api/YmServer/getUserInfoApi`，`token`,`type=score` → `data.score`
- 报错退分：`POST http://api.jfbym.com/api/YmServer/refundApi`，`token`,`uniqueCode`（部分接口支持；**勿乱报错，可能冻号**）

### 3.4 常用 type（customApi）
| 用途 | type | 单价(低至) |
|---|---|---|
| 双图滑块 | `20111` | ¥0.01（返回 px） |
| 单图滑块 | `22222` / `20225` | ¥0.008 |
| alx 滑块 | `20226` | ¥0.01 |
| 通用坐标点选 | `30009` / `88888` | ¥0.016–0.025 |
| 文字点选 | `30100` 等 | ¥0.01 |
| reCAPTCHA v2 token | `40010` | ¥0.032 |
| reCAPTCHA v3 token | `40011` | ¥0.032 |
| hCaptcha token | `50013` | ¥0.032 |
| Cloudflare Turnstile | `40012` | ¥0.02 |
| 通用数英 | `10110` 等 | ¥0.002 起 |

---

## 4. 类型 → 平台 → 接口 速查

| 类型 | 首选平台 | 接口/type | 路线 |
|---|---|---|---|
| reCAPTCHA v2/v3 | YesCaptcha | `NoCaptchaTaskProxyless` / `RecaptchaV3TaskProxyless` | R1 |
| reCAPTCHA v2/v3 | JFBYM | `funnelApi` `40010/40011` | R1 |
| hCaptcha | YesCaptcha | `HCaptchaTaskProxyless` | R1 |
| hCaptcha | JFBYM | `funnelApi` `50013` | R1 |
| Turnstile | YesCaptcha | `TurnstileTaskProxyless` | R1 |
| Turnstile | JFBYM | `40012` | R1 |
| 滑块(8类) | BingTop | GT3：`gt3_capture`+还原+按 §2.3.1 选 type；其他见 §2.3 | R2 |
| 滑块(8类) | JFBYM | `20111` slide_image+background_image | R2 |
| 滑块(8类) | 协议 | 移交 captcha-slide-reverse | R3 |
| 点选/坐标 | BingTop | `13202/13134/13242` | R2 |
| 点选/坐标 | JFBYM | `30009/30100` + extra | R2 |
| 旋转 | BingTop | `11201`/`1120`/`11212`（见 `bingtop_types.py`） | R2 |
| 京东登录 JCAP | BingTop | 按题型：`11201`(旋转)/`3002`(轨迹)/`1310`(滑块) | R2（`jd-login-captcha`） |
| 旋转 | JFBYM | 旋转 type + 角度 | R2 |
| 图文/字符/计算 | BingTop | `10001/10011/12012` | R1-like |
| 图文/字符/计算 | JFBYM | `10110` 等 | R1-like |
| 图文/字符 | YesCaptcha | `ImageToTextTask` | R1-like |
| 轨迹 | BingTop/JFBYM | `3002` | R2/R3 |

> 判定原则：**token 类优先 YesCaptcha（有中国节点、协议标准）**；**图片/滑块/点选/旋转优先 BingTop（最便宜、类型全）或 JFBYM（均衡、2captcha 风格）**；**滑块要零依赖规模化则走 R3 协议**。
