#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JFBYM 云码 适配器（内置）。2captcha 风格，类型最均衡；图片 customApi、token funnelApi。"""
import time

from adapters.base import BaseSolver, register, post_json


@register
class JFBYM(BaseSolver):
    name = "jfbym"
    display = "JFBYM 云码"
    supports = {"token": True, "image": True, "slide": True, "click": True, "rotate": False}
    secret_fields = ["token"]

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.custom = "http://api.jfbym.com/api/YmServer/customApi"
        self.funnel = "http://api.jfbym.com/api/YmServer/funnelApi"
        self.funnel_result = "http://api.jfbym.com/api/YmServer/funnelApiResult"

    def _tok(self):
        t = self.secret("token", "JFBYM_TOKEN")
        if not t:
            raise SystemExit(
                "missing jfbym token；请先运行 python scripts/setup.py 配置，或设环境变量 JFBYM_TOKEN"
            )
        return t

    def _unpack(self, r):
        if r.get("code") not in (10000, 10001):
            raise RuntimeError(f"JFBYM error: {r}")
        return r.get("data", {}).get("data")

    def solve_image(self, b64, captcha_type=None, **extra):
        return self._unpack(post_json(self.custom, {"image": b64, "token": self._tok(), "type": str(captcha_type), **extra}))

    def solve_slide(self, slice_b64=None, bg_b64=None, captcha_type="20111", **extra):
        return self._unpack(post_json(self.custom, {
            "slide_image": slice_b64, "background_image": bg_b64,
            "token": self._tok(), "type": str(captcha_type), **extra,
        }))

    def solve_click(self, b64, extra_text=None, captcha_type=None, **extra):
        return self._unpack(post_json(self.custom, {
            "image": b64, "token": self._tok(), "type": str(captcha_type),
            "extra": extra_text, **extra,
        }))

    def solve_token(self, captcha_type="40010", googlekey=None, pageurl=None, **extra):
        if not (googlekey and pageurl):
            raise SystemExit("jfbym token 需要 googlekey(sitekey) + pageurl")
        payload = {"token": self._tok(), "type": str(captcha_type), "googlekey": googlekey, "pageurl": pageurl}
        payload.update(extra)
        r = post_json(self.funnel, payload)
        if r.get("code") != 10001:
            raise RuntimeError(f"JFBYM funnel step1 error: {r}")
        cap_id = r["data"]["captchaId"]
        rec_id = r["data"]["recordId"]
        for _ in range(40):
            rr = post_json(self.funnel_result, {"token": self._tok(), "captchaId": cap_id, "recordId": rec_id})
            if rr.get("code") == 10001:
                return rr
            if rr.get("code") == 10010:
                raise RuntimeError(f"JFBYM funnel failed: {rr}")
            time.sleep(3)  # 10004/10009 限流，退避重试
        raise RuntimeError("JFBYM funnel timeout")
