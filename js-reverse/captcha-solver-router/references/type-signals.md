# 验证码类型识别信号

给 `scripts/identify.py` 和人工判断用的信号表。优先级：具体厂商信号 > 通用类别信号。识别不出时向用户要截图或 JS/网络样本。

## 一、Token 类（平台 R1 直接出令牌）

| 类型 | 关键信号（HTML/JS/网络） | 路由 |
|---|---|---|
| reCAPTCHA v2 | `recaptcha/api.js`、`g-recaptcha`、`data-sitekey=6L…`、`api2/userverify`、`anchor`、`g-recaptcha-response` | R1（YesCaptcha/JFBYM） |
| reCAPTCHA v3 | `grecaptcha.execute`、`data-action=`、`6L…` sitekey、无 checkbox、隐形 | R1（YesCaptcha/JFBYM） |
| hCaptcha | `hcaptcha.com/1/api.js`、`data-hcaptcha-widget-id`、`bf_token`、`h-captcha-response` | R1（YesCaptcha/JFBYM） |
| FunCaptcha (Arkose) | `funcaptcha`、`enforcement.play`、`arkoselabs`、`blob:`、`fc-token` | R1（JFBYM 等） |
| Cloudflare Turnstile | `challenges.cloudflare.com`、`cf-turnstile`、`rResponse`、`turnstile` | R1（YesCaptcha/JFBYM） |
| Cloudflare 5s 盾 | 整页 `Just a moment…`、`cf_clearance` cookie、含 Turnstile 但会整页跳转 | R1（YesCaptcha `CloudFlareTaskS2`，质量差） |

## 二、滑块类（R2 平台双图滑块 / R3 协议脚本）

> 以下 8 类信号直接复用 `captcha-slide-reverse`，并附其首选 R3 分支。

| 厂商 | 关键信号 | R3 分支 |
|---|---|---|
| 极验 GT3 | `register-slide`、`gettype.php`、`fullpage.9.x`、`slide.7.x`、`apiv6.geetest.com/get.php`、`api.geevisit.com/ajax.php`、`$_BCm`、`validate/seccode` | gt3 |
| 极验 GT4 | `captcha_id`、`lot_number`、`pow_detail`、`payload`、`process_token`、`/gcaptcha4.geetest.com/load`、`/verify`、`w` | gt4 |
| 腾讯滑块 | `TDC`、`getData(true)`、`TCaptcha`、`slide.js`、`cap_union_prehandle`、`cap_union_new_verify`、`collect`、`eks` | tencent |
| 网易易盾 | `NECaptcha`、`c.dun.163.com/api/v3/get`、`/api/v3/check`、`cb`、`data`、`token`、`front/bg` | yidun |
| 数美滑块 | `captcha1.fengkongcloud.cn/ca/v1/register`、`/ca/v2/fverify`、`captchaUuid`、`rid`、`sm.js` | shumei |
| 云片滑块 | `captcha.yunpian.com/v1/jsonp/captcha/get`、`ypjsonp`、`captchaId`、`yp_riddler_id`、`yp.js` | yunpian |
| 360 天御 | `captcha.jiagu.360.cn/api/v3/auth`、`/api/v3/check`、`360CaptchaSDK`、`captchaId`、`k`、`decryptImage` | tianyu360 |
| 顶象/鼎象 | `dingxiang-sdk.js`、`greenseer.js`、`_dx.UA`、`/api/a`、`/api/p1`、`/api/p2`、`/api/v1`、`4012 POSITION_MISMATCH` | dingxiang |
| 京东 JCAP | `passport.jd.com`、`#captcha_modal`、`captcha_modal_pc`、`使图片为正`、`轨迹绘制`、`JDJRV` | jcap |

通用滑块补充信号：`drag`、`slider`、`缺口`、`slice/fullbg/bg`、`trace/track`、`轨迹`、`mousemove`。

## 三、点选 / 坐标类（R2 平台返回坐标）

| 类型 | 关键信号 | 路由 |
|---|---|---|
| 通用坐标点选 | `请点击`、`click`、`坐标`、`tuple`、`按顺序` | R2（BingTop/JFBYM） |
| 文字点选 | `请依次点选`、`文字点选`、`点选文字逗号隔开`、字符图 | R2（需传 extra 汉字） |
| 语序点选 | `语序`、`依次点击汉字` | R2 |
| 空间推理 | `空间推理`、`点击侧对着你的字母`、`请点击…` | R2 |
| 九宫格/六宫格 | `九宫格`、`六宫格`、`宫格` | R2 |
| 图标点选 | `图标点选`、`icon` | R2 |

## 四、旋转类（R2 平台返回角度）

| 类型 | 关键信号 | 路由 |
|---|---|---|
| 单图旋转 | `rotate`、`旋转`、`角度`、`使图片为正`、单图 | R2（BingTop `11201`/`1120`，换算有效行程拖拽） |
| 双图/内外圈旋转 | `双旋转`、`tk`、`内圈/外圈` | R2 |
| 内旋转 | `内旋转`、`中间圆`、`1-359` | R2 |

## 五、图文 / 字符 / 计算题（R1-like ImageToText）

| 类型 | 关键信号 | 路由 |
|---|---|---|
| 数字英文 | `captcha.php`、`code`、`validateCode`、4-6 位字符图 | R1-like（ImageToText） |
| 中文 | `中文`、`汉字`、字符图 | R1-like |
| 计算题 | `计算题`、`1+2=?`、`?` 运算图 | R1-like |
| 问答 | `问答题`、`图中描述` | R1-like |

## 六、轨迹类（R2 回放 / R3）

| 类型 | 关键信号 | 路由 |
|---|---|---|
| 轨迹验证 | `轨迹`、`gesture`、`按标题返回坐标序列`、`箭头方向`、`按图中轨迹` | R2（BingTop `3002` 回放）/R3 |

## 七、识别输出约定

`identify.py` 输出 JSON：

```json
{
  "category": "slide|token|click|rotate|image|track",
  "platform": "gt4|tencent|yidun|...|recaptcha_v2|hcaptcha|...",
  "confidence": "high|medium|low",
  "evidence": ["匹配到的信号片段"],
  "routes": ["R1", "R2", "R3"],
  "recommended_platform": "yescaptcha|bingtop|jfbym"
}
```

`confidence=low` 时，流程应在第 1 步停下，向用户索取截图/样本，不进入路由。
