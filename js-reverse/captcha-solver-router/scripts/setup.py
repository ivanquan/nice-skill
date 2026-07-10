#!/usr/bin/env python3
# captcha-solver-router / scripts/setup.py
# 首次配置向导：把打码平台密钥写进**项目目录** config.json（不在 skill 内）。
# 密钥只在本地文件里，绝不进入聊天 / 版本库；输入用 getpass 不回显。
#
# 用法：cd <你的项目根目录> && python <skill>/scripts/setup.py

import getpass
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from config_paths import resolve_config_path, resolve_config_example_path


def ask(platform, fields):
    """交互式询问单个平台的密钥字段。"""
    print(f"\n--- {platform} ---")
    have = input(f"你是否已有 {platform} 的密钥？(y/n，默认 n): ").strip().lower()
    if have != "y":
        return None
    out = {}
    for field, secret in fields:
        prompt = f"  请输入 {platform}.{field}（输入不回显）: " if secret \
            else f"  请输入 {platform}.{field}: "
        val = getpass.getpass(prompt) if secret else input(prompt)
        if val:
            out[field] = val
    return out or None


def ensure_scaffold(cfg_path):
    """若项目 config.json 不存在，从模板复制空骨架。"""
    if os.path.exists(cfg_path):
        return False
    example = resolve_config_example_path()
    if os.path.exists(example):
        with open(example, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"external_adapters": []}
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"已从模板创建 {cfg_path}，接下来填写你已有的平台密钥。\n")
    return True


def main():
    """配置向导入口：写入项目根目录 config.json。"""
    cfg_path = resolve_config_path(prefer_existing=True)
    print(f"配置将写入: {cfg_path}")
    print("（可通过环境变量 CAPTCHA_ROUTER_CONFIG 指定其他绝对路径）\n")
    if not os.path.exists(cfg_path):
        ensure_scaffold(cfg_path)
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except json.JSONDecodeError:
            cfg = {}
    yes = ask("yescaptcha", [("client_key", True), ("node", False)])
    if yes:
        cfg["yescaptcha"] = yes
    bing = ask("bingtop", [("username", False), ("password", True)])
    if bing:
        cfg["bingtop"] = bing
    jfbym = ask("jfbym", [("token", True)])
    if jfbym:
        cfg["jfbym"] = jfbym

    print("\n--- automation（R2 浏览器 / R3 远程调试，可选）---")
    want_auto = input("是否配置本机 Chrome 路径？(y/n，默认 n): ").strip().lower()
    auto_cfg = dict(cfg.get("automation") or {})
    if want_auto == "y":
        print("  示例 Windows: C:/Program Files/Google/Chrome/Application/chrome.exe")
        print("  示例 macOS:   /Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        print("  示例 Linux:   /usr/bin/google-chrome")
        chrome = input("  chrome_executable（留空跳过）: ").strip()
        if chrome:
            auto_cfg["chrome_executable"] = chrome
        port = input("  chrome_debug_port（R3/MCP 用，默认 9222，回车跳过）: ").strip()
        if port.isdigit():
            auto_cfg["chrome_debug_port"] = int(port)
    if auto_cfg:
        cfg["automation"] = auto_cfg

    merged = dict(cfg)
    for platform, section in [("yescaptcha", yes), ("bingtop", bing), ("jfbym", jfbym)]:
        if section:
            merged[platform] = {**(merged.get(platform) or {}), **section}
    if auto_cfg:
        merged["automation"] = {**(merged.get("automation") or {}), **auto_cfg}

    if not any(k in merged for k in ("yescaptcha", "bingtop", "jfbym", "automation")):
        print("\n未配置任何项。你可稍后重跑本向导，或手动编辑项目 config.json。")
        print("预检：python preflight.py --route R1")
        return

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\n已写入 {cfg_path}（项目本地文件，请勿提交到版本库）。")
    print("验证：python preflight.py --json")


if __name__ == "__main__":
    main()
