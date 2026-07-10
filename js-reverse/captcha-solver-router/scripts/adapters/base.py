#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
captcha-solver-router 适配器基类 + 注册表。

所有打码平台（内置 + 用户外接）都实现 BaseSolver 接口，并在模块导入时用
@register 注册到 REGISTRY。solve.py 通过 discover() 自动加载 scripts/adapters/
目录下的内置适配器，以及 config.json 中 external_adapters 列出的用户外接 .py。

外接平台作者只需：
  1. 复制 scripts/adapters/template.py 为 myplatform.py
  2. 填 name / display / supports / 各 solve_* 方法
  3. 把它放进 scripts/adapters/ 或在 config.json 的 external_adapters 登记路径
  4. python solve.py --platform myplatform ...
"""

import base64
import importlib.util
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# name -> class
REGISTRY = {}


def register(cls):
    """适配器类装饰器：把类注册进 REGISTRY（以 cls.name 为键）。"""
    if not getattr(cls, "name", ""):
        raise RuntimeError(f"适配器 {cls.__name__} 必须定义类属性 name")
    REGISTRY[cls.name] = cls
    return cls


class BaseSolver:
    # ---- 每个适配器必须定义的元信息 ----
    name = ""                                    # 小写唯一标识，如 "yescaptcha"
    display = ""                                 # 中文展示名，如 "YesCaptcha"
    supports = {                                 # 该平台支持的操作
        "token": False, "image": False, "slide": False,
        "click": False, "rotate": False, "track": False,
    }
    secret_fields = []                           # 需要的密钥字段（写入 config.json）

    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    # ---- 密钥读取：config.json 的 {platform: {...}} 段，回退到环境变量 ----
    def secret(self, field, env_name=None):
        v = (self.cfg.get(field) or "").strip()
        if not v and env_name:
            v = (os.environ.get(env_name) or "").strip()
        return v

    # ---- 子类必须实现的四个操作（按 supports 启用） ----
    def solve_token(self, **kw):
        raise NotImplementedError(f"{self.name} 未实现 solve_token")

    def solve_image(self, **kw):
        raise NotImplementedError(f"{self.name} 未实现 solve_image")

    def solve_slide(self, **kw):
        raise NotImplementedError(f"{self.name} 未实现 solve_slide")

    def solve_click(self, **kw):
        raise NotImplementedError(f"{self.name} 未实现 solve_click")

    def solve_rotate(self, **kw):
        raise NotImplementedError(f"{self.name} 未实现 solve_rotate")

    def solve_track(self, **kw):
        raise NotImplementedError(f"{self.name} 未实现 solve_track")

    # ---- 统一调度入口 ----
    def solve(self, op, **kw):
        if not self.supports.get(op):
            raise SystemExit(
                f"平台 {self.display or self.name} 不支持操作 '{op}'（supports={self.supports}）"
            )
        return {
            "token": self.solve_token,
            "image": self.solve_image,
            "slide": self.solve_slide,
            "click": self.solve_click,
            "rotate": self.solve_rotate,
            "track": self.solve_track,
        }[op](**kw)


# ---------------------------------------------------------------------------
# HTTP / 图像辅助（所有适配器复用）
# ---------------------------------------------------------------------------
def post_json(url, payload, timeout=60, headers=None):
    data = (payload if isinstance(payload, (bytes, str)) else json_dumps(payload)).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json_loads(r.read().decode("utf-8"))


def post_form(url, payload, timeout=60):
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json_loads(r.read().decode("utf-8"))


def img_to_b64(path):
    if not path or not os.path.exists(path):
        raise SystemExit(f"image not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def json_loads(s):
    import json
    return json.loads(s)


# ---------------------------------------------------------------------------
# 注册表发现
# ---------------------------------------------------------------------------
def discover(adapters_dir, external_paths=None, extra_imports=None):
    """
    导入内置适配器（adapters_dir 下除 base/__init__/template 外的 .py），
    以及 config.json 中 external_adapters 列出的外接 .py 绝对路径。
    返回 REGISTRY（name -> class）。
    """
    # 确保 scripts/ 在 sys.path，使适配器可用 `from adapters.base import ...`
    scripts_dir = os.path.dirname(os.path.abspath(adapters_dir))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    _import_file(os.path.join(adapters_dir, "_builtins_order.py")) if os.path.exists(
        os.path.join(adapters_dir, "_builtins_order.py")
    ) else None

    # 内置适配器：adapters_dir 下所有 .py（排除保留名）
    skip = {"base.py", "__init__.py", "template.py", "_builtins_order.py"}
    if os.path.isdir(adapters_dir):
        for fn in sorted(os.listdir(adapters_dir)):
            if fn in skip or not fn.endswith(".py"):
                continue
            _import_file(os.path.join(adapters_dir, fn))

    # 外接适配器：config.json 中的 external_adapters（绝对路径列表）
    for p in (external_paths or []):
        if not os.path.exists(p):
            print(f"[warn] external adapter not found: {p}", file=sys.stderr)
            continue
        _import_file(p)

    # 额外由调用方直接提供的模块路径
    for p in (extra_imports or []):
        _import_file(p)

    return REGISTRY


def _import_file(path):
    name = "adapters_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # 模块顶层用 @register 注册；也兼容直接赋值 SOLVER = Class
    if hasattr(mod, "SOLVER") and getattr(mod.SOLVER, "name", ""):
        register(mod.SOLVER)
