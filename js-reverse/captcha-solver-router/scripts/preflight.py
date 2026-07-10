#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
captcha-solver-router 环境与配置预检。

在识别/路由/调平台/自动化/R3 侦察前，检查本地基础配置是否就绪；
缺失项给出可执行的引导步骤（含密钥配置向导），密钥绝不打印到 stdout。

用法：
  python preflight.py                    # 全量预检
  python preflight.py --route R1         # 只检查 R1 所需项
  python preflight.py --route R2 --backend cloak
  python preflight.py --platform yescaptcha
  python preflight.py --init             # 从 config.example.json 生成空 config.json 骨架
  python preflight.py --json             # 标准 JSON 信封输出
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_PATH = os.path.join(HERE, "config.example.json")
ADAPTERS_DIR = os.path.join(HERE, "adapters")


def _cfg_path():
    """返回当前项目 config.json 路径。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from config_paths import resolve_config_path
    return resolve_config_path(prefer_existing=True)

# 平台密钥字段 → 环境变量回退名
PLATFORM_ENV = {
    "yescaptcha": {"client_key": "YESCAPTCHA_KEY"},
    "bingtop": {"username": "BINGTOP_USER", "password": "BINGTOP_PASS"},
    "jfbym": {"token": "JFBYM_TOKEN"},
}

# 占位符：视为未配置
PLACEHOLDER_RE = re.compile(
    r"^(YOUR_|your_|changeme|placeholder|xxx+|todo|<.*>)$",
    re.I,
)

ROUTE_HINTS = {
    "router": "Router 识别无需密钥；可直接 python identify.py --text \"...\"",
    "R1": "R1 需至少一家 token 平台密钥（YesCaptcha/JFBYM）；运行 python scripts/setup.py",
    "R2": "R2 需滑块/点选平台密钥 + 反爬浏览器后端；密钥 setup.py，浏览器见 references/automation.md",
    "R3": "R3 无需打码平台密钥；需 JSReverser-MCP + 可选 Chrome 远程调试，见 references/mcp-integration.md",
}


def _load_config():
    """读取项目 config.json；不存在则返回空 dict。"""
    path = _cfg_path()
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_placeholder(val):
    """判断配置值是否为占位符或未填。"""
    if val is None:
        return True
    s = str(val).strip()
    if not s:
        return True
    if PLACEHOLDER_RE.match(s):
        return True
    if s.upper().startswith("YOUR_"):
        return True
    return False


def _get_registry(config):
    """加载适配器注册表。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from adapters.base import discover
    external = config.get("external_adapters") or []
    return discover(ADAPTERS_DIR, external_paths=external)


def _secret_status(platform, field, cfg_section):
    """检查单个密钥字段是否已通过 config 或环境变量配置。"""
    val = (cfg_section.get(field) or "").strip()
    env_name = PLATFORM_ENV.get(platform, {}).get(field)
    env_val = (os.environ.get(env_name) or "").strip() if env_name else ""
    effective = val if not _is_placeholder(val) else env_val
    if _is_placeholder(effective):
        return {
            "field": field,
            "configured": False,
            "source": None,
            "env_fallback": env_name,
        }
    return {
        "field": field,
        "configured": True,
        "source": "config" if not _is_placeholder(val) else "env",
        "env_fallback": env_name,
    }


def check_config_file():
    """检查项目 config.json 是否存在。"""
    cfg_path = _cfg_path()
    exists = os.path.exists(cfg_path)
    example_exists = os.path.exists(EXAMPLE_PATH)
    item = {
        "id": "config_json",
        "ok": exists,
        "path": cfg_path,
        "message": "config.json 已存在" if exists else "config.json 不存在",
    }
    if not exists:
        item["guide"] = (
            "在项目根目录运行：python <skill>/scripts/setup.py\n"
            "或复制 config.example.json 为项目根目录 config.json 后本地填写密钥\n"
            "或：python preflight.py --init（在当前工作目录生成骨架）"
        )
    elif example_exists:
        item["guide"] = "密钥只存本地 config.json；缺字段时运行 python setup.py 补填"
    return item


def check_platform_secrets(config, registry, platform_filter=None):
    """检查各打码平台密钥是否就绪。"""
    results = []
    for name, cls in sorted(registry.items()):
        if platform_filter and name != platform_filter:
            continue
        fields = getattr(cls, "secret_fields", []) or []
        if not fields:
            continue
        section = config.get(name, {}) if isinstance(config.get(name), dict) else {}
        field_status = [_secret_status(name, f, section) for f in fields]
        all_ok = all(s["configured"] for s in field_status)
        entry = {
            "id": f"platform_{name}",
            "platform": name,
            "display": getattr(cls, "display", name),
            "ok": all_ok,
            "fields": field_status,
            "supports": {k: v for k, v in getattr(cls, "supports", {}).items() if v},
        }
        if not all_ok:
            missing = [s["field"] for s in field_status if not s["configured"]]
            envs = [s["env_fallback"] for s in field_status if not s["configured"] and s["env_fallback"]]
            entry["message"] = f"{name} 缺少: {', '.join(missing)}"
            entry["guide"] = (
                f"运行：cd scripts && python setup.py\n"
                f"选择 {getattr(cls, 'display', name)} 并输入 {', '.join(missing)}（输入不回显）\n"
            )
            if envs:
                entry["guide"] += f"或设置环境变量：{', '.join(envs)}\n"
            entry["guide"] += "切勿在对话中粘贴明文密钥；误发请去平台重置。"
        else:
            entry["message"] = f"{name} 密钥已配置"
        results.append(entry)
    return results


def check_route_platforms(config, registry, route):
    """按路线检查是否至少有一家可用平台。"""
    token_ok = any(
        p["ok"] for p in check_platform_secrets(config, registry)
        if p["platform"] in ("yescaptcha", "jfbym") and "token" in p.get("supports", {})
    )
    slide_ok = any(
        p["ok"] for p in check_platform_secrets(config, registry)
        if p["platform"] in ("bingtop", "jfbym") and p.get("supports", {}).get("slide")
    )
    image_ok = any(
        p["ok"] for p in check_platform_secrets(config, registry)
        if p.get("supports", {}).get("image")
    )

    if route == "R1":
        ok = token_ok or image_ok
        return {
            "id": "route_R1",
            "ok": ok,
            "message": "R1 可用" if ok else "R1 无可用平台密钥",
            "guide": None if ok else (
                "至少配置一家：YesCaptcha（token 首选）或 JFBYM（token 备选）\n"
                "运行：cd scripts && python setup.py"
            ),
            "token_ready": token_ok,
            "image_ready": image_ok,
        }
    if route == "R2":
        ok = slide_ok or image_ok
        return {
            "id": "route_R2",
            "ok": ok,
            "message": "R2 平台侧可用" if ok else "R2 无滑块/点选平台密钥",
            "guide": None if ok else (
                "配置 BingTop 或 JFBYM：cd scripts && python setup.py\n"
                "另需反爬浏览器后端，见 --backend 检查"
            ),
            "slide_ready": slide_ok,
        }
    if route == "R3":
        return {
            "id": "route_R3",
            "ok": True,
            "message": "R3 不依赖打码平台密钥",
            "guide": "确认 JSReverser-MCP 与 Chrome 远程调试（见 mcp 检查项）",
        }
    return None


def check_python_version():
    """检查 Python 版本是否 >= 3.8。"""
    v = sys.version_info
    ok = v >= (3, 8)
    return {
        "id": "python",
        "ok": ok,
        "message": f"Python {v.major}.{v.minor}.{v.micro}",
        "guide": None if ok else "需要 Python 3.8+",
    }


def check_backend(backend):
    """检查 automate.py 指定后端是否可导入。"""
    packages = {
        "cloak": ("cloakbrowser", "pip install cloakbrowser"),
        "drissionpage": ("DrissionPage", "pip install DrissionPage"),
        "playwright": ("playwright", "pip install playwright && playwright install chromium"),
    }
    if backend not in packages:
        return {"id": f"backend_{backend}", "ok": False, "message": f"未知后端 {backend}"}
    mod_name, install_hint = packages[backend]
    spec = importlib.util.find_spec(mod_name)
    ok = spec is not None
    return {
        "id": f"backend_{backend}",
        "ok": ok,
        "backend": backend,
        "message": f"{backend} 后端可用" if ok else f"{backend} 未安装（{mod_name}）",
        "guide": None if ok else install_hint,
    }


def check_chrome_executable(config):
    """检查 config.json 是否配置了本机 Chrome 可执行文件（R2 Playwright 可选）。"""
    auto = (config or {}).get("automation") or {}
    exe = (auto.get("chrome_executable") or os.environ.get("CHROME_EXECUTABLE") or "").strip()
    if not exe:
        return {
            "id": "chrome_executable",
            "ok": None,
            "message": "未配置 chrome_executable（Playwright 将使用自带 Chromium）",
            "guide": (
                "在本机运行 python setup.py 填写 automation.chrome_executable，\n"
                "或设环境变量 CHROME_EXECUTABLE，或在 automate.py 传 --chrome-path"
            ),
        }
    ok = os.path.isfile(exe)
    return {
        "id": "chrome_executable",
        "ok": ok,
        "path": exe,
        "message": f"Chrome 路径已配置且{'存在' if ok else '不存在'}: {exe}",
        "guide": None if ok else "请修正 config.json automation.chrome_executable 或重新运行 setup.py",
    }


def check_chrome_debug(port=9222, chrome_exe=None):
    """探测 Chrome 远程调试端口是否可达。"""
    url = f"http://127.0.0.1:{port}/json/version"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {
            "id": "chrome_debug",
            "ok": True,
            "port": port,
            "message": f"Chrome 远程调试端口 {port} 可达",
            "browser": data.get("Browser", ""),
        }
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        exe_hint = chrome_exe or "<你的 Chrome 路径>"
        return {
            "id": "chrome_debug",
            "ok": False,
            "port": port,
            "message": f"Chrome 远程调试端口 {port} 未开启",
            "guide": (
                f'示例：\n  "{exe_hint}" '
                f'--remote-debugging-port={port} --user-data-dir="<临时用户目录>"\n'
                "Chrome 路径见 config.json automation.chrome_executable（setup.py 配置）\n"
                "详见 references/mcp-integration.md §2.2"
            ),
        }


def init_config_scaffold():
    """在当前项目目录生成 config.json 骨架（不在 skill 目录）。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from config_paths import resolve_config_path, resolve_config_example_path
    cfg_path = resolve_config_path(prefer_existing=False)
    example_path = resolve_config_example_path()
    if os.path.exists(cfg_path):
        return {"created": False, "path": cfg_path, "reason": "config.json 已存在，未覆盖"}
    if os.path.exists(example_path):
        with open(example_path, encoding="utf-8") as f:
            example = json.load(f)
    else:
        example = {"external_adapters": []}
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(example, f, indent=2, ensure_ascii=False)
    return {"created": True, "path": cfg_path, "source": "config.example.json"}


def run_preflight(route=None, platform=None, backend=None, chrome_port=9222, with_project=False, vendor="unknown"):
    """执行预检并汇总结果。"""
    config = _load_config()
    registry = _get_registry(config)
    checks = []

    checks.append(check_python_version())
    checks.append(check_config_file())
    checks.extend(check_platform_secrets(config, registry, platform_filter=platform))

    if route and route != "router":
        rp = check_route_platforms(config, registry, route)
        if rp:
            checks.append(rp)

    if route in (None, "R2", "R3", "all") or backend:
        for b in ([backend] if backend else ["cloak", "drissionpage", "playwright"]):
            if backend or route in (None, "R2", "all"):
                checks.append(check_backend(b))

    if route in (None, "R2", "R3", "all"):
        checks.append(check_chrome_executable(config))
        auto = config.get("automation") or {}
        port = int(auto.get("chrome_debug_port") or chrome_port)
        exe = (auto.get("chrome_executable") or os.environ.get("CHROME_EXECUTABLE") or "").strip()
        checks.append(check_chrome_debug(port, chrome_exe=exe or None))
    if route in (None, "R3", "all"):
        checks.append({
                "id": "mcp_js_reverse",
                "ok": None,
                "message": "JSReverser-MCP 需在 Cursor/客户端 mcp.json 中配置（本脚本无法自动验证）",
                "guide": (
                    "1. 构建 JSReverser-MCP：node build/src/index.js\n"
                    "2. 在 MCP 配置加入 js-reverse 服务器（绝对路径）\n"
                    "3. R3 侦察可选 --browserUrl http://127.0.0.1:9222\n"
                    "详见 references/mcp-integration.md §2"
                ),
            })

    # 去重：同 id 保留最后一个
    seen = {}
    for c in checks:
        seen[c["id"]] = c
    checks = list(seen.values())

    failed = [c for c in checks if c.get("ok") is False]
    all_ok = len(failed) == 0

    data = {
        "ready": all_ok,
        "route": route or "all",
        "checks": checks,
        "failed_count": len(failed),
        "route_hint": ROUTE_HINTS.get(route or "", ROUTE_HINTS.get("router")),
        "next_steps": [c["guide"] for c in failed if c.get("guide")],
    }
    if with_project:
        from project_detect import detect_project
        eff_route = route if route and route != "all" else "R2"
        data["project"] = detect_project(vendor=vendor, route=eff_route)
    return {
        "success": all_ok,
        "data": data,
        "error": None if all_ok else f"{len(failed)} 项检查未通过，请按 guide 配置后重跑 preflight.py",
    }


def format_human(envelope):
    """把 JSON 信封格式化为终端可读文本。"""
    lines = []
    d = envelope["data"]
    lines.append(f"预检结果: {'通过' if envelope['success'] else '未通过'} ({d['failed_count']} 项失败)")
    if d.get("route_hint"):
        lines.append(f"路线说明: {d['route_hint']}")
    lines.append("")
    for c in d["checks"]:
        if c.get("ok") is True:
            mark = "[OK]"
        elif c.get("ok") is False:
            mark = "[FAIL]"
        else:
            mark = "[INFO]"
        lines.append(f"  {mark} {c.get('message', c.get('id', ''))}")
    guides = d.get("next_steps") or []
    if guides:
        lines.append("")
        lines.append("--- 引导 ---")
        for i, g in enumerate(guides, 1):
            lines.append(f"{i}. {g.strip()}")
    if not envelope["success"]:
        lines.append("")
        lines.append("配置密钥：cd scripts && python setup.py（输入不回显，勿在聊天粘贴密钥）")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="captcha-solver-router 配置预检")
    ap.add_argument("--route", choices=["router", "R1", "R2", "R3", "all"], default="all")
    ap.add_argument("--platform", help="只检查指定平台密钥")
    ap.add_argument("--backend", choices=["cloak", "drissionpage", "playwright"])
    ap.add_argument("--chrome-port", type=int, default=9222)
    ap.add_argument("--init", action="store_true", help="从 config.example.json 生成 config.json 骨架")
    ap.add_argument("--json", action="store_true", help="输出标准 JSON 信封")
    ap.add_argument("--with-project", action="store_true",
                    help="在 JSON 中附带 project_detect 结果（框架/配置路径/产物推荐）")
    ap.add_argument("--vendor", default="unknown", help="配合 --with-project：验证码厂商标识")
    ap.add_argument("--detect-project", action="store_true",
                    help="仅输出项目框架与路径推荐（等同 project_detect.py）")
    args = ap.parse_args()

    if args.detect_project:
        from project_detect import detect_project
        route = None if args.route == "all" else args.route
        eff_route = route if route else "router"
        result = detect_project(vendor=args.vendor, route=eff_route)
        envelope = {"success": True, "data": result, "error": None}
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return

    if args.init:
        result = init_config_scaffold()
        envelope = {"success": True, "data": result, "error": None}
        if args.json:
            print(json.dumps(envelope, ensure_ascii=False, indent=2))
        else:
            if result.get("created"):
                print(f"已创建 {result['path']}（请运行 python setup.py 填写密钥，或本地编辑）")
            else:
                print(result.get("reason", "未创建"))
        return

    route = None if args.route == "all" else args.route
    envelope = run_preflight(
        route=route,
        platform=args.platform,
        backend=args.backend,
        chrome_port=args.chrome_port,
        with_project=args.with_project,
        vendor=args.vendor,
    )

    if args.json:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
    else:
        print(format_human(envelope))
    sys.exit(0 if envelope["success"] else 1)


if __name__ == "__main__":
    main()
