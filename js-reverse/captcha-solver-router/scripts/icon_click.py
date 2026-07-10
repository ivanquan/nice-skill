#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用图标点选验证码 R2 流程：厂商 Provider + 打码平台识别 + 拟人点击。

易盾仅为内置 Provider 之一（click_providers.yidun），CLI: --op icon-click --click-provider yidun
"""

from click_providers import resolve_icon_provider
from recaptcha_grid import HumanPacer
from yidun_click import (
    _log_stealth_status,
    load_click_solver,
    parse_click_coords,
)

# 各平台图标点选默认 captchaType（双图：背景 + 图标提示）
# 冰拓：13242=双图点选（本账号已验证）；13202/13134 需单独开通
DEFAULT_ICON_CLICK_TYPE = {
    "bingtop": 13242,
    "jfbym": 30009,
}
# 仅 captcha type 错误时换类型
BINGTOP_ICON_FALLBACK = [13242, 1324, 1315]
BINGTOP_RATE_LIMIT_SLEEP = 8.0
HINT_WAIT_TIMEOUT = 10


def _is_bingtop_rate_limit(exc):
    """判断冰拓是否为限流（请稍后再试），区别于 captcha type error 或无效图片。"""
    text = str(exc)
    return "请稍后再试" in text or "稍后再试" in text


def classify_icon_click(platform, bg_b64, hint_b64=None, extra_text=None, captcha_type=None):
    """调用打码平台识别图标点选坐标（背景截图 + 图标提示截图）。"""
    solver = load_click_solver(platform)
    ctype = captcha_type or DEFAULT_ICON_CLICK_TYPE.get(platform)
    if ctype is None:
        raise RuntimeError(f"平台 {platform} 未配置默认 icon captcha_type")

    use_hint = bool(hint_b64) and hint_b64 != bg_b64
    types_to_try = [ctype]
    if platform == "bingtop":
        types_to_try = [ctype] + [t for t in BINGTOP_ICON_FALLBACK if t != ctype]

    last_exc = None
    for t in types_to_try:
        try:
            if platform == "bingtop":
                return solver.solve_click(
                    bg_b64,
                    extra_text=extra_text or None,
                    hint_b64=hint_b64 if use_hint else None,
                    captcha_type=t,
                )
            extra = {"extra": extra_text} if extra_text else {}
            if use_hint and platform == "jfbym":
                extra["image2"] = hint_b64
            return solver.solve_click(bg_b64, extra_text=extra_text, captcha_type=t, **extra)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if _is_bingtop_rate_limit(exc):
                raise RuntimeError(
                    f"BingTop 限流(请稍后再试)，建议间隔 {BINGTOP_RATE_LIMIT_SLEEP}s 后重试"
                ) from exc
            if "type error" in msg or "captcha type" in msg:
                print(f"[icon-click] BingTop type={t} 未开通，尝试下一类型", flush=True)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("图标点选识别失败")


def solve_icon_click(
    page,
    platform,
    provider_name="auto",
    captcha_type=None,
    widget_selector=None,
    auto_trigger=True,
    max_rounds=3,
    humanize_factor=1.3,
):
    """
    通用图标点选：Provider 负责 DOM → 平台识别坐标 → 拟人点击。
    """
    pacer = HumanPacer(humanize_factor)
    provider = resolve_icon_provider(provider_name, page, widget_selector)
    provider.prepare()
    _log_stealth_status(page)

    last_error = None
    if auto_trigger:
        if not provider.trigger(pacer):
            return {
                "ok": False,
                "rounds": 0,
                "points": [],
                "instruction": "",
                "provider": provider.name,
                "last_error": "页面上未找到验证码 widget",
            }
        if not provider.wait_ready(pacer):
            return {
                "ok": False,
                "rounds": 0,
                "points": [],
                "instruction": provider.read_instruction(),
                "provider": provider.name,
                "last_error": "点击后未出现图标点选面板",
            }

    rounds = 0
    while rounds < max_rounds:
        if provider.is_success():
            return {
                "ok": True,
                "rounds": rounds,
                "points": [],
                "instruction": provider.read_instruction(),
                "provider": provider.name,
                "last_error": None,
            }

        if not provider.panel_visible():
            if rounds == 0 and auto_trigger:
                provider.trigger(pacer)
                provider.wait_ready(pacer)
            elif rounds > 0:
                provider.reload(pacer)
                pacer.pause(1.0, 1.8)
            else:
                last_error = "验证码面板不可见"
                break

        instruction, hint_b64 = provider.wait_hint(pacer, timeout_sec=HINT_WAIT_TIMEOUT)
        if not hint_b64:
            last_error = f"图标提示图等待超时({HINT_WAIT_TIMEOUT}s): {instruction!r}"
            print(f"[icon-click] {last_error}，刷新挑战", flush=True)
            provider.reload(pacer)
            rounds += 1
            continue

        try:
            if not provider.panel_visible():
                provider._hover_float_bar(pacer)
                pacer.pause(0.5, 1.0)
            bg_b64, img_sel, natural_wh = provider.capture_bg_b64()
        except Exception as exc:
            last_error = f"截图失败: {exc}"
            pacer.pause(1.0, 1.5)
            rounds += 1
            continue

        expected = provider.expected_click_count(hint_b64)
        points = []
        raw = None
        try:
            raw = classify_icon_click(
                platform,
                bg_b64,
                hint_b64=hint_b64,
                extra_text=instruction or None,
                captcha_type=captcha_type,
            )
            points = parse_click_coords(raw)
        except Exception as exc:
            last_error = f"平台识别失败: {exc}"
            print(f"[icon-click] 识别异常: {exc}", flush=True)
            if "限流" in str(exc) or "请稍后再试" in str(exc):
                import time
                time.sleep(BINGTOP_RATE_LIMIT_SLEEP)
                break
            pacer.pause(1.5, 2.5)
            rounds += 1
            continue

        if not points:
            last_error = f"平台未返回有效坐标: {raw!r}"
            rounds += 1
            continue

        if len(points) > expected:
            points = points[:expected]

        print(
            f"[icon-click] 第 {rounds + 1} 轮 provider={provider.name} "
            f"题面={instruction!r} 点击={points}",
            flush=True,
        )
        try:
            provider.click_points(img_sel, points, pacer, natural_wh=natural_wh)
        except Exception as exc:
            last_error = f"点击失败: {exc}"
            rounds += 1
            continue

        pacer.pause(2.5, 4.0)
        for _ in range(3):
            if provider.is_success():
                rounds += 1
                return {
                    "ok": True,
                    "rounds": rounds,
                    "points": points,
                    "instruction": instruction,
                    "provider": provider.name,
                    "last_error": None,
                }
            pacer.pause(0.8, 1.2)
        rounds += 1
        last_error = "点击完成但未检测到验证成功，可能坐标偏差"

    return {
        "ok": provider.is_success(),
        "rounds": rounds,
        "points": [],
        "instruction": provider.read_instruction(),
        "provider": provider.name,
        "last_error": last_error,
    }
