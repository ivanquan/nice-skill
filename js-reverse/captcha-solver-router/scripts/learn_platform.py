#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
learn_platform.py —— 根据「新打码平台 API 规格」生成适配器骨架。

流程（skill 调研完新平台 API 后）：
  1. 把从文档/首页提取的接口信息整理成一个 spec JSON（见下方 SPEC 说明）。
  2. 运行本脚本生成 scripts/adapters/<name>.py 骨架：
       python scripts/learn_platform.py --spec spec.json
       python scripts/learn_platform.py --spec spec.json --write     # 真正落盘
       python scripts/learn_platform.py --spec spec.json --dry-run   # 仅预览
  3. 打开生成的 .py，补全各 solve_* 里的「按你的平台…」解析逻辑。
  4. 在 scripts/config.json 的 external_adapters 登记路径（若放在 scripts/adapters/ 外），
     或直接丢进 scripts/adapters/ 即可被自动发现。

SPEC 字段（均可空，缺失的会留 TODO）：
{
  "name": "newcap",                 # 小写唯一标识
  "display": "NewCap",              # 中文展示名
  "base_url": "https://api.newcap.com",
  "auth": {"field": "token", "env": "NEWCAP_TOKEN"},   # 密钥字段名 + 环境变量名
  "supports": ["token", "image", "slide"],             # 该平台支持的操作
  "endpoints": {
    "create": "https://api.newcap.com/createTask",
    "result": "https://api.newcap.com/getTaskResult",
    "image":  "https://api.newcap.com/image",
    "slide":  "https://api.newcap.com/slide"
  },
  "notes": "从 https://newcap.com/docs 提取：createTask 轮询 getTaskResult …"
}
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTERS_DIR = os.path.join(HERE, "adapters")


def render(spec):
    name = (spec.get("name") or "newplatform").strip().lower()
    display = spec.get("display") or name
    base_url = spec.get("base_url") or "https://api.example.com"
    auth = spec.get("auth") or {}
    auth_field = auth.get("field") or "api_key"
    auth_env = auth.get("env") or (name.upper() + "_KEY").replace("-", "_")
    supports = spec.get("supports") or []
    ep = spec.get("endpoints") or {}
    notes = spec.get("notes") or ""
    sup = {k: bool(k in supports) for k in ("token", "image", "slide", "click", "rotate")}
    sup_py = repr(sup)

    def ep_or(k, default):
        return ep.get(k) or default

    create_ep = ep_or("create", base_url.rstrip("/") + "/createTask")
    result_ep = ep_or("result", base_url.rstrip("/") + "/getTaskResult")
    image_ep = ep_or("image", base_url.rstrip("/") + "/image")
    slide_ep = ep_or("slide", base_url.rstrip("/") + "/slide")

    t_token = f"""
    def solve_token(self, task_type=None, website_url=None, website_key=None, **extra):
        # 调研备注: {notes}
        # 1) 提交任务
        r = post_json("{create_ep}", {{
            "{auth_field}": self.{auth_field},
            "task": {{"type": task_type or "NoCaptchaTaskProxyless",
                     "websiteURL": website_url, "websiteKey": website_key, **extra}},
        }})
        # TODO: 按本平台返回结构取任务 id，并轮询 {result_ep} 直到完成
        return r
"""
    t_image = f"""
    def solve_image(self, b64, captcha_type=None, **extra):
        # 调研备注: {notes}
        r = post_json("{image_ep}", {{
            "{auth_field}": self.{auth_field}, "body": b64, "type": captcha_type, **extra,
        }})
        # TODO: 按本平台返回结构取出答案（字符串/数字）
        return r.get("data", {{}}).get("answer")
"""
    t_slide = f"""
    def solve_slide(self, slice_b64=None, bg_b64=None, captcha_type=None, **extra):
        # 调研备注: {notes}
        r = post_json("{slide_ep}", {{
            "{auth_field}": self.{auth_field}, "slide": slice_b64,
            "background": bg_b64, "type": captcha_type, **extra,
        }})
        # TODO: 返回像素距离（数字）或坐标
        return r.get("data", {{}}).get("offset")
"""
    t_click = f"""
    def solve_click(self, b64, extra_text=None, captcha_type=None, **extra):
        # 调研备注: {notes}
        r = post_json("{image_ep}", {{
            "{auth_field}": self.{auth_field}, "image": b64,
            "extra": extra_text, "type": captcha_type, **extra,
        }})
        return r.get("data", {{}}).get("points")
"""
    t_rotate = f"""
    def solve_rotate(self, b64, captcha_type=None, **extra):
        # 调研备注: {notes}
        r = post_json("{image_ep}", {{
            "{auth_field}": self.{auth_field}, "image": b64, "type": captcha_type, **extra,
        }})
        return r.get("data", {{}}).get("angle")
"""

    body = ""
    if sup["token"]:
        body += t_token
    if sup["image"]:
        body += t_image
    if sup["slide"]:
        body += t_slide
    if sup["click"]:
        body += t_click
    if sup["rotate"]:
        body += t_rotate

    code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{display} 适配器（由 learn_platform.py 生成骨架，待补全解析逻辑）。"""
from adapters.base import BaseSolver, register, post_json, post_form, img_to_b64


@register
class {display.replace(" ", "")}Adapter(BaseSolver):
    name = "{name}"
    display = "{display}"
    supports = {sup_py}
    secret_fields = ["{auth_field}"]

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.{auth_field} = self.secret("{auth_field}", "{auth_env}")
        self.base_url = "{base_url}"
{body}
'''
    return name, code


def main():
    ap = argparse.ArgumentParser(description="根据 spec 生成外接打码平台适配器骨架")
    ap.add_argument("--spec", required=True, help="spec JSON 文件路径（含新平台 API 信息）")
    ap.add_argument("--write", action="store_true", help="真正写入 scripts/adapters/<name>.py（默认仅预览）")
    ap.add_argument("--dry-run", action="store_true", help="仅预览（同默认）")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    name, code = render(spec)
    out_path = os.path.join(ADAPTERS_DIR, f"{name}.py")

    print("=" * 60)
    print(f"将生成适配器: {name}  ->  {out_path}")
    print("=" * 60)
    print(code)
    print("=" * 60)

    if args.write:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[ok] 已写入 {out_path}")
        print("下一步：")
        print(f"  1. 补全各 solve_* 里的 TODO 解析逻辑（参考调研备注）")
        print(f"  2. 在 scripts/config.json 的 {name} 段填入 {spec.get('auth', {}).get('field', 'api_key')}")
        print(f"  3. python scripts/solve.py --platform {name} --op ... 测试")
    else:
        print("[dry-run] 未写入文件。加 --write 落盘。")


if __name__ == "__main__":
    main()
