#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定位项目级 config.json（配置放在用户项目目录，不放在 skill 目录）。

优先级：
  1. 环境变量 CAPTCHA_ROUTER_CONFIG（绝对路径）
  2. 从当前工作目录向上查找 config.json（跳过 skill/scripts 内部）
  3. 默认写入目标：当前工作目录/config.json
"""

import os

SKILL_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _is_skill_scripts_dir(directory):
    """判断目录是否为 captcha-solver-router 的 scripts 目录。"""
    return os.path.normcase(os.path.abspath(directory)) == os.path.normcase(SKILL_SCRIPTS_DIR)


def resolve_config_path(prefer_existing=True):
    """
    解析 config.json 路径。

    prefer_existing=True 时向上查找已存在的项目 config；
    否则直接返回当前目录下的 config.json（供 setup 写入）。
    """
    env_path = (os.environ.get("CAPTCHA_ROUTER_CONFIG") or "").strip()
    if env_path:
        return os.path.abspath(env_path)

    if prefer_existing:
        cur = os.path.abspath(os.getcwd())
        for _ in range(12):
            if not _is_skill_scripts_dir(cur):
                candidate = os.path.join(cur, "config.json")
                if os.path.isfile(candidate):
                    return candidate
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

    return os.path.join(os.getcwd(), "config.json")


def resolve_config_example_path():
    """返回 skill 自带的 config.example.json 模板路径。"""
    return os.path.join(SKILL_SCRIPTS_DIR, "config.example.json")


def load_project_config():
    """加载项目 config.json，不存在则返回空 dict。"""
    import json
    path = resolve_config_path(prefer_existing=True)
    if not os.path.isfile(path):
        return {}, path
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), path
    except (OSError, json.JSONDecodeError):
        return {}, path
