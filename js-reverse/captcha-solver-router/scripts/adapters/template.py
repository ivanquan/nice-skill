#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外接打码平台适配器模板。复制本文件为 myplatform.py，填入你的平台信息即可。

用法：
  1. cp scripts/adapters/template.py scripts/adapters/myplatform.py
  2. 修改下方 name / display / supports / secret_fields 与各 solve_* 方法
  3. 把 myplatform.py 留在 scripts/adapters/ 即可被自动发现；
     或把它放任意位置，在 scripts/config.json 的 external_adapters 登记绝对路径
  4. python scripts/solve.py --platform myplatform --op ... 

可用的辅助函数（from adapters.base import）：
  post_json(url, payload, timeout, headers)  -> dict   # JSON POST
  post_form(url, payload, timeout)           -> dict   # form-urlencoded POST
  img_to_b64(path)                           -> str    # 图片转 base64（不带前缀）
  self.secret(field, env_name)               -> str    # 读 config.json 或环境变量
"""


from adapters.base import BaseSolver, register, post_json, post_form, img_to_b64


@register
class MyPlatform(BaseSolver):
    # ---- 元信息（必改） ----
    name = "myplatform"                 # 小写唯一标识，--platform 用它
    display = "MyPlatform"              # 中文展示名
    supports = {                        # 该平台支持哪些操作
        "token": False, "image": False, "slide": False,
        "click": False, "rotate": False,
    }
    secret_fields = ["api_key"]         # 需要的密钥字段（写入 config.json 对应段）

    # ---- 初始化：可在此解析 config 段 ----
    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.api_key = self.secret("api_key", "MYPLATFORM_KEY")
        self.base_url = "https://api.myplatform.com"

    # ---- 各操作实现（按 supports 启用，不需要的删掉或保留 raise） ----
    def solve_token(self, task_type=None, website_url=None, website_key=None, **extra):
        # 示例：2captcha 兼容的 createTask / getTaskResult
        r = post_json(f"{self.base_url}/createTask", {
            "clientKey": self.api_key,
            "task": {"type": task_type or "NoCaptchaTaskProxyless",
                     "websiteURL": website_url, "websiteKey": website_key, **extra},
        })
        # TODO: 按你的平台轮询 getTaskResult，返回包含令牌的结果 dict
        return r

    def solve_image(self, b64, captcha_type=None, **extra):
        r = post_json(f"{self.base_url}/solve", {
            "key": self.api_key, "body": b64, "type": captcha_type, **extra,
        })
        # TODO: 按你的平台返回结构取出答案（字符串/数字）
        return r.get("data", {}).get("answer")

    def solve_slide(self, slice_b64=None, bg_b64=None, captcha_type=None, **extra):
        r = post_json(f"{self.base_url}/slide", {
            "key": self.api_key, "slide": slice_b64, "background": bg_b64,
            "type": captcha_type, **extra,
        })
        # TODO: 返回像素距离（数字）或坐标
        return r.get("data", {}).get("offset")

    def solve_click(self, b64, extra_text=None, captcha_type=None, **extra):
        r = post_json(f"{self.base_url}/click", {
            "key": self.api_key, "image": b64, "extra": extra_text,
            "type": captcha_type, **extra,
        })
        return r.get("data", {}).get("points")

    def solve_rotate(self, b64, captcha_type=None, **extra):
        r = post_json(f"{self.base_url}/rotate", {
            "key": self.api_key, "image": b64, "type": captcha_type, **extra,
        })
        return r.get("data", {}).get("angle")
