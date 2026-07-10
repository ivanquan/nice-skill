#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YesCaptcha 适配器（内置）。2captcha 兼容，token 类最强，无滑块类。"""
import time

from adapters.base import BaseSolver, register, post_json


@register
class YesCaptcha(BaseSolver):
    name = "yescaptcha"
    display = "YesCaptcha"
    supports = {"token": True, "image": True, "slide": False, "click": False, "rotate": False}
    secret_fields = ["client_key"]

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.node = self.cfg.get("node") or "https://api.yescaptcha.com"

    def _key(self):
        k = self.secret("client_key", "YESCAPTCHA_KEY")
        if not k:
            raise SystemExit(
                "missing yescaptcha client_key；请先运行 python scripts/setup.py 配置，或设环境变量 YESCAPTCHA_KEY"
            )
        return k

    def _create(self, task):
        return post_json(f"{self.node}/createTask", {"clientKey": self._key(), "task": task})

    def _result(self, task_id, max_wait=150):
        for _ in range(max_wait // 3 + 1):
            r = post_json(f"{self.node}/getTaskResult", {"clientKey": self._key(), "taskId": task_id})
            if r.get("status") == "ready":
                return r
            time.sleep(3)
        return r

    def solve_token(self, task_type=None, website_url=None, website_key=None, **extra):
        if not (website_url and website_key):
            raise SystemExit("yescaptcha token 需要 website_url + website_key（sitekey）")
        task_type = task_type or "NoCaptchaTaskProxyless"
        task = {"type": task_type, "websiteURL": website_url, "websiteKey": website_key}
        extra = {k: v for k, v in extra.items() if v is not None}
        task.update(extra)
        r = self._create(task)
        if r.get("errorId") != 0:
            raise RuntimeError(f"YesCaptcha createTask error: {r}")
        return self._result(r["taskId"])

    def solve_image(self, b64, task_type="ImageToTextTask", **extra):
        r = self._create({"type": task_type, "body": b64, **extra})
        if r.get("errorId") != 0:
            raise RuntimeError(f"YesCaptcha createTask error: {r}")
        return self._result(r["taskId"])

    def solve_recaptcha_v2_classification(self, image_b64, question, confidence=0.5):
        """reCAPTCHA v2 九宫格/十六宫格识别，返回含 solution.objects 的结果。"""
        task = {
            "type": "ReCaptchaV2Classification",
            "image": image_b64,
            "question": question,
        }
        if confidence is not None:
            task["confidence"] = confidence
        r = self._create(task)
        if r.get("errorId") != 0:
            raise RuntimeError(f"YesCaptcha ReCaptchaV2Classification error: {r}")
        if r.get("status") == "ready" and r.get("solution"):
            return r
        return self._result(r["taskId"], max_wait=60)
