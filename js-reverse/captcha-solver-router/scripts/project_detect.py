#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
探测用户项目框架，并给出 config.json 与验证码产物（测试脚本/集成模块）的推荐路径。

Agent 在创建任何项目内文件前应先运行本脚本，把输出展示给用户并等待确认路径。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from config_paths import resolve_config_path, SKILL_SCRIPTS_DIR


def _norm(path):
    """规范化路径为绝对路径字符串。"""
    return os.path.normpath(os.path.abspath(path))


def _is_skill_internal(directory):
    """判断目录是否落在 captcha-solver-router skill 内部（不应作为用户项目根）。"""
    d = _norm(directory)
    skill_root = _norm(os.path.dirname(SKILL_SCRIPTS_DIR))
    return d == _norm(SKILL_SCRIPTS_DIR) or d.startswith(skill_root + os.sep)


def find_project_root(start=None, markers=None):
    """
    从 start 向上查找项目根目录（命中常见标记文件/目录即停止）。
    跳过 skill/scripts 目录本身；找不到标记时回退为 start（cwd），绝不返回盘符根。
    """
    markers = markers or [
        ".git",
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "manage.py",
    ]
    start_abs = _norm(start or os.getcwd())
    cur = start_abs
    fallback = start_abs

    for _ in range(16):
        if _is_skill_internal(cur):
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
            continue
        if any(os.path.exists(os.path.join(cur, m)) for m in markers):
            return cur
        # 盘符根（如 D:\）不作为项目根
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    # 若 cwd 向上已有 config.json，以其所在目录作为弱推断根
    cfg = list_config_candidates(start_abs)
    if cfg.get("resolved") and os.path.isfile(cfg["resolved"]):
        return _norm(os.path.dirname(cfg["resolved"]))

    return fallback


def list_config_candidates(start=None):
    """
    列出从 start 向上能找到的 config.json 候选路径（不含 skill/scripts 内）。
    """
    cur = _norm(start or os.getcwd())
    found = []
    default_write = _norm(os.path.join(cur, "config.json"))
    for _ in range(12):
        if not _is_skill_internal(cur):
            candidate = os.path.join(cur, "config.json")
            if os.path.isfile(candidate):
                found.append(_norm(candidate))
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    env_path = (os.environ.get("CAPTCHA_ROUTER_CONFIG") or "").strip()
    env_abs = _norm(env_path) if env_path else None
    resolved = resolve_config_path(prefer_existing=True)
    return {
        "cwd": _norm(start or os.getcwd()),
        "env_override": env_abs,
        "resolved": _norm(resolved),
        "candidates": found,
        "default_write_if_missing": default_write,
    }


def detect_framework(project_root):
    """
    根据项目根目录下的标记文件推断技术栈与目录习惯。
    """
    root = _norm(project_root)
    signals = []
    framework = "generic"
    language = "python"
    layout = {}

    def has(name):
        return os.path.exists(os.path.join(root, name))

    if has("manage.py") and (has("settings.py") or os.path.isdir(os.path.join(root, "apps"))):
        framework = "django"
        signals.append("manage.py")
    elif has("pyproject.toml") or has("requirements.txt") or has("setup.py"):
        if os.path.isdir(os.path.join(root, "src")):
            framework = "python-src-layout"
            layout["package_root"] = os.path.join(root, "src")
            signals.append("src/")
        else:
            framework = "python-flat"
        if has("feapder"):
            framework = "feapder"
            signals.append("feapder")
    if has("package.json"):
        framework = "node" if framework == "generic" else f"{framework}+node"
        signals.append("package.json")
        language = "mixed"
    if has("scrapy.cfg"):
        framework = "scrapy"
        signals.append("scrapy.cfg")
    if has("go.mod"):
        framework = "go"
        language = "go"
        signals.append("go.mod")

    tests_dir = None
    for name in ("tests", "test", "spec"):
        p = os.path.join(root, name)
        if os.path.isdir(p):
            tests_dir = p
            break

    scripts_dir = os.path.join(root, "scripts")
    if not os.path.isdir(scripts_dir):
        scripts_dir = None

    layout.update({
        "project_root": root,
        "tests_dir": tests_dir,
        "scripts_dir": scripts_dir,
    })
    return {
        "framework": framework,
        "language": language,
        "signals": signals,
        "layout": layout,
    }


def suggest_artifact_paths(project_root, framework_info, vendor="unknown", route="R2"):
    """
    按项目框架推荐验证码相关产物的落盘位置（须用户确认后再创建）。
    """
    root = _norm(project_root)
    fw = framework_info.get("framework", "generic")
    tests = framework_info.get("layout", {}).get("tests_dir")
    scripts = framework_info.get("layout", {}).get("scripts_dir")

    safe_vendor = "".join(c if c.isalnum() or c in "-_" else "_" for c in (vendor or "captcha"))
    test_name = f"{safe_vendor}_captcha_test.py"

    if fw == "django":
        integration = os.path.join(root, "apps", "captcha", "services.py")
        test_path = os.path.join(tests or root, test_name)
    elif fw == "scrapy":
        integration = os.path.join(root, "captcha_solver", "middlewares.py")
        test_path = os.path.join(root, test_name)
    elif fw == "feapder":
        integration = os.path.join(root, "feapder", "utils", "captcha_solver.py")
        test_path = os.path.join(root, test_name)
    elif tests:
        test_path = os.path.join(tests, test_name)
        integration = os.path.join(root, "captcha", "solver.py")
    elif scripts:
        test_path = os.path.join(scripts, test_name)
        integration = os.path.join(root, "captcha", "solver.py")
    else:
        test_path = os.path.join(root, test_name)
        integration = os.path.join(root, "captcha", "solver.py")

    skill_only = {
        "automate_cli": os.path.join(SKILL_SCRIPTS_DIR, "automate.py"),
        "solve_cli": os.path.join(SKILL_SCRIPTS_DIR, "solve.py"),
        "note": "通用引擎留在 skill/scripts；项目内只放薄封装测试脚本或业务集成",
    }

    return {
        "config_json": os.path.join(root, "config.json"),
        "test_script_recommended": _norm(test_path),
        "integration_module_recommended": _norm(integration),
        "skill_scripts": skill_only,
        "route": route,
        "vendor": vendor,
        "rule": "创建前必须向用户展示本表并获明确确认；不得默认写入 skill 目录或 Agent 臆测路径",
    }


def detect_project(start=None, vendor="unknown", route="R2"):
    """
    汇总项目探测结果，供 Agent 在停步检查点展示给用户。
    """
    cwd = _norm(start or os.getcwd())
    root = find_project_root(cwd)
    fw = detect_framework(root)
    cfg = list_config_candidates(cwd)
    artifacts = suggest_artifact_paths(root, fw, vendor=vendor, route=route)
    return {
        "cwd": cwd,
        "project_root": root,
        "framework": fw,
        "config": cfg,
        "artifacts": artifacts,
        "agent_must_confirm": [
            "config.json 最终路径（resolved 或用户指定 CAPTCHA_ROUTER_CONFIG）",
            "打码平台名称与 captchaType（R1/R2）",
            "test_script_recommended 是否创建、路径是否修改",
            "integration_module_recommended 是否创建、路径是否修改",
        ],
    }


def main():
    """CLI：输出项目探测 JSON 信封。"""
    import argparse
    ap = argparse.ArgumentParser(description="探测项目框架与验证码产物推荐路径")
    ap.add_argument("--cwd", default=None, help="起始目录（默认当前工作目录）")
    ap.add_argument("--vendor", default="unknown", help="验证码厂商标识，用于命名测试脚本")
    ap.add_argument("--route", default="R2", choices=["R1", "R2", "R3", "router"])
    ap.add_argument("--json", action="store_true", help="输出 JSON（默认即 JSON）")
    args = ap.parse_args()
    result = detect_project(start=args.cwd, vendor=args.vendor, route=args.route)
    envelope = {"success": True, "data": result, "error": None}
    print(json.dumps(envelope, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
