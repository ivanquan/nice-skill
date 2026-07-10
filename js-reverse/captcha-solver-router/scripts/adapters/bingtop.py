#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BingTop 冰拓 适配器（内置）。自研 API，阻塞式单次返回，类型极全、价格最低。"""
import json
import os
import urllib.parse

from adapters.base import BaseSolver, register, post_form, img_to_b64
from bingtop_types import warn_deprecated_type


def _bingtop_debug_enabled():
    """是否打印冰拓请求/响应调试日志（默认开启，设 BINGTOP_DEBUG=0 关闭）。"""
    return os.environ.get("BINGTOP_DEBUG", "1").strip().lower() not in ("0", "false", "no", "off")


def _mask_secret(value, keep=2):
    """脱敏账号/密码，仅保留前后若干字符。"""
    text = str(value or "")
    if len(text) <= keep * 2:
        return "*" * len(text)
    return f"{text[:keep]}***{text[-keep:]}"


def _summarize_b64_field(name, value):
    """摘要 base64 字段：长度、前缀、是否像 JPEG/PNG、md5。"""
    if not value:
        return f"{name}=<empty>"
    text = str(value)
    head = text[:24]
    kind = "unknown"
    if text.startswith("/9j/"):
        kind = "jpeg-b64"
    elif text.startswith("iVBOR"):
        kind = "png-b64"
    import hashlib
    digest = hashlib.md5(text.encode("ascii", errors="ignore")).hexdigest()[:12]
    return f"{name}=len:{len(text)} kind:{kind} md5:{digest} head:{head}..."


def _decode_image_b64_info(b64_text):
    """解码 base64 并校验是否为可识别的图片文件。"""
    import base64
    import io
    if not b64_text:
        return {"valid": False, "error": "empty"}
    try:
        raw = base64.b64decode(b64_text, validate=True)
    except Exception as exc:
        return {"valid": False, "error": f"base64 decode failed: {exc}"}

    fmt = "unknown"
    if raw[:3] == b"\xff\xd8\xff":
        fmt = "jpeg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        fmt = "png"
    elif raw[:6] in (b"GIF87a", b"GIF89a"):
        fmt = "gif"

    info = {
        "valid": fmt != "unknown",
        "format": fmt,
        "file_bytes": len(raw),
        "magic_hex": raw[:4].hex(),
    }
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        info["width"] = int(img.size[0])
        info["height"] = int(img.size[1])
        info["pil_ok"] = True
    except Exception as exc:
        info["pil_ok"] = False
        info["pil_error"] = str(exc)
    return info


def _log_bingtop_request(url, payload):
    """打印冰拓请求字段摘要（不含完整图片 base64）。"""
    cap = payload.get("captchaData") or ""
    sub = payload.get("subCaptchaData") or ""
    same_image = False
    if cap and sub and len(str(sub)) > 80:
        import hashlib
        same_image = hashlib.md5(str(cap).encode()).hexdigest() == hashlib.md5(str(sub).encode()).hexdigest()

    summary = {
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "url": url,
        "username": _mask_secret(payload.get("username")),
        "password": _mask_secret(payload.get("password")),
        "captchaType": payload.get("captchaType"),
        "captchaData": _summarize_b64_field("captchaData", cap),
        "subCaptchaData": (
            _summarize_b64_field("subCaptchaData", sub)
            if sub and len(str(sub)) > 80
            else f"subCaptchaData={sub!r}"
        ),
        "same_image_md5": same_image,
    }
    print("[bingtop][request]", flush=True)
    for key, val in summary.items():
        print(f"  {key}: {val}", flush=True)
    if cap and len(str(cap)) > 80:
        print(f"  captchaData_decode: {_decode_image_b64_info(str(cap))}", flush=True)
    if sub and len(str(sub)) > 80:
        print(f"  subCaptchaData_decode: {_decode_image_b64_info(str(sub))}", flush=True)


def _log_bingtop_response(response):
    """打印冰拓完整响应 JSON。"""
    print("[bingtop][response]", flush=True)
    print(f"  raw: {json.dumps(response, ensure_ascii=False)}", flush=True)
    print(f"  code: {response.get('code')!r}", flush=True)
    print(f"  message: {response.get('message')!r}", flush=True)
    data = response.get("data")
    if isinstance(data, dict):
        print(f"  data.recognition: {data.get('recognition')!r}", flush=True)


@register
class BingTop(BaseSolver):
    name = "bingtop"
    display = "BingTop 冰拓"
    supports = {"token": False, "image": True, "slide": True, "click": True, "rotate": True, "track": True}
    secret_fields = ["username", "password"]

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.url = "https://www.bingtop.com/ocr/upload/"

    def _cred(self):
        u = self.secret("username", "BINGTOP_USER")
        p = self.secret("password", "BINGTOP_PASS")
        if not (u and p):
            raise SystemExit(
                "missing bingtop username/password；请先运行 python scripts/setup.py 配置，或设环境变量 BINGTOP_USER / BINGTOP_PASS"
            )
        return u, p

    def _solve(self, captcha_type, image_b64, sub_b64=None, sub_text=None):
        if captcha_type is None:
            raise SystemExit("bingtop 需要 --captcha-type（整数类型 ID，见 https://www.bingtop.com/type/）")
        warn_deprecated_type(captcha_type)
        u, p = self._cred()
        payload = {
            "username": u,
            "password": p,
            "captchaType": int(captcha_type),
            "captchaData": image_b64,
        }
        if sub_b64:
            payload["subCaptchaData"] = sub_b64
        elif sub_text:
            # 1315/1324/13152 等：subCaptchaData 为标题文字（1315 需 URL 编码）
            if int(captcha_type) in (1315,):
                payload["subCaptchaData"] = urllib.parse.quote(sub_text, safe="")
            else:
                payload["subCaptchaData"] = sub_text
        if _bingtop_debug_enabled():
            _log_bingtop_request(self.url, payload)
        r = post_form(self.url, payload, timeout=60)
        if _bingtop_debug_enabled():
            _log_bingtop_response(r)
        if r.get("code") != 0:
            raise RuntimeError(f"BingTop error {r.get('code')}: {r.get('message')}")
        return r["data"]["recognition"]

    def solve_image(self, b64, captcha_type=None, **extra):
        return self._solve(captcha_type, b64)

    def solve_slide(self, slice_b64=None, bg_b64=None, captcha_type=None, **extra):
        # BingTop 双图滑块：captchaData=还原后的背景图，subCaptchaData=滑块小图
        # 极验 GT3 乱序 bg 须先用 gt3_restore.py / gt3_capture.py / solve.py --gt3-restore 还原
        # captchaType 须按 references/platforms.md §2.3.1 与冰拓文档试跑选定，勿写死
        if not bg_b64 or not slice_b64:
            raise SystemExit("bingtop slide 需要背景 bg + 滑块 slice 两张图的 base64")
        return self._solve(captcha_type, bg_b64, slice_b64)

    def solve_click(self, b64, extra_text=None, hint_b64=None, captcha_type=None, **extra):
        """点选识别；hint_b64 为图标提示图（subCaptchaData）。"""
        sub_img = hint_b64 or extra.get("hint_b64") or extra.get("sub_b64")
        if sub_img:
            return self._solve(captcha_type, b64, sub_b64=sub_img, sub_text=extra_text)
        return self._solve(captcha_type, b64, sub_text=extra_text)

    def solve_rotate(self, b64, captcha_type=None, **extra):
        return self._solve(captcha_type, b64)

    def solve_track(self, b64, captcha_type=None, **extra):
        """轨迹绘制识别；返回坐标序列字符串。"""
        return self._solve(captcha_type, b64)
