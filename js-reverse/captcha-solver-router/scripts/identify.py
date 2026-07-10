#!/usr/bin/env python3
# captcha-solver-router / scripts/identify.py
# 启发式验证码类型识别：从 HTML/JS/网络 dump 或 HAR 中匹配信号，
# 输出 {category, platform, confidence, evidence, routes, recommended_platform}。
#
# 用法：
#   python identify.py --text "<html/js/network dump>"
#   python identify.py --har path/to/har.json

import argparse
import json
import sys

# (platform, category, [信号片段])
SIGNALS = [
    ("recaptcha_v2", "token", ["recaptcha/api.js", "g-recaptcha", "data-sitekey=6l", "api2/userverify"]),
    ("recaptcha_v3", "token", ["grecaptcha.execute", "data-action=", "grecaptcha.render"]),
    ("hcaptcha", "token", ["hcaptcha.com/1/api.js", "data-hcaptcha-widget-id", "bf_token", "h-captcha-response"]),
    ("funcaptcha", "token", ["funcaptcha", "arkoselabs", "enforcement.play", "fc-token"]),
    ("turnstile", "token", ["challenges.cloudflare.com", "cf-turnstile", "rresponse", "turnstile"]),
    ("cf5s", "token", ["cf_clearance", "just a moment", "cf-mitigated"]),
    ("gt3", "slide", ["register-slide", "gettype.php", "fullpage.9.x", "slide.7.x", "apiv6.geetest.com/get.php", "ajax.php", "validate-slide"]),
    ("gt4", "slide", ["captcha_id", "lot_number", "pow_detail", "gcaptcha4.geetest.com/load", "process_token", "/verify"]),
    ("tencent", "slide", ["window.tdc", "getdata(true)", "tcaptcha", "cap_union_prehandle", "cap_union_new_verify"]),
    ("yidun", "slide", ["necaptcha", "api/v3/get", "api/v3/check", "dun.163.com", "yidun"]),
    ("shumei", "slide", ["captcha1.fengkongcloud.cn", "/ca/v1/register", "/ca/v2/fverify", "captchauuid"]),
    ("yunpian", "slide", ["captcha.yunpian.com", "ypjsonp", "yp_riddler_id", "yp.js"]),
    ("tianyu360", "slide", ["captcha.jiagu.360.cn", "/api/v3/auth", "/api/v3/check", "360captchasdk"]),
    ("dingxiang", "slide", ["dingxiang-sdk.js", "greenseer.js", "_dx.ua", "/api/a", "/api/p1", "/api/v1", "position_mismatch"]),
    ("click", "click", ["请点击", "请依次点选", "文字点选", "九宫格", "六宫格", "坐标", "tuple", "语序", "空间推理"]),
    ("rotate", "rotate", ["旋转", "角度", "双旋转", "内旋转", "rotate"]),
    ("image", "image", ["captcha.php", "validatecode", "计算题", "问答题", "中文", "数英", "code.php"]),
    ("track", "track", ["轨迹", "gesture", "箭头方向", "按标题返回坐标序列", "track_data"]),
]

REC_PLATFORM = {
    "token": "yescaptcha",
    "slide": "bingtop",
    "click": "bingtop",
    "rotate": "bingtop",
    "image": "bingtop",
    "track": "bingtop",
}
ROUTES = {
    "token": ["R1"],
    "slide": ["R2", "R3"],
    "click": ["R2"],
    "rotate": ["R2"],
    "image": ["R1-like"],
    "track": ["R2", "R3"],
}


def identify(text):
    low = text.lower()
    hits = {}
    for platform, category, pats in SIGNALS:
        matched = [p for p in pats if p.lower() in low]
        if matched:
            hits[platform] = (category, matched)
    if not hits:
        return None
    best = max(hits.items(), key=lambda kv: (len(kv[1][1]), 0))
    platform, category, evidence = best[0], best[1][0], best[1][1]
    conf = "high" if len(evidence) >= 2 else "medium"
    return {
        "category": category,
        "platform": platform,
        "confidence": conf,
        "evidence": evidence,
        "routes": ROUTES[category],
        "recommended_platform": REC_PLATFORM[category],
        "all_hits": {k: v[0] for k, v in hits.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="HTML/JS/network dump text")
    ap.add_argument("--har", help="path to HAR json file")
    a = ap.parse_args()

    text = a.text or ""
    if a.har:
        with open(a.har, encoding="utf-8") as f:
            har = json.load(f)
        for e in har.get("log", {}).get("entries", []):
            req = e.get("request", {})
            text += req.get("url", "") + " "
            text += json.dumps(req.get("postData", {}), ensure_ascii=False) + " "

    if not text.strip():
        print(json.dumps({"error": "no input"}, ensure_ascii=False))
        sys.exit(1)

    res = identify(text)
    if not res:
        res = {"category": None, "confidence": "low",
               "note": "no signal matched, ask user for screenshot / JS+network sample"}
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
