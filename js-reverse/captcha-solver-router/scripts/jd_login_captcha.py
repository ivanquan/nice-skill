#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京东登录页验证码 Demo：自动识别轨迹 / 旋转 / 滑块，并调用通用 R2 解法。
"""

import time

from captcha_type_detect import DEFAULT_WIDGET, detect_captcha_category, format_detection_log
from jd_jcap_slide import (
    install_jd_jcap_hook,
    is_jd_captcha_success,
    jd_captcha_overlay_visible,
    measure_jd_rotate_track_width,
    solve_jd_jcap_slide,
    trigger_jd_pwd_login,
)
from recaptcha_grid import HumanPacer
from rotate_captcha import solve_rotate_captcha
from track_draw import solve_track_draw

from bingtop_types import CATEGORY_TYPE_LABEL, resolve_captcha_type


def wait_jd_captcha_panel(page, widget_selector=None, timeout_sec=40, pacer=None):
    """等待京东验证码浮层出现，并打印探测日志。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    last_hint = ""
    while time.time() < deadline:
        if jd_captcha_overlay_visible(page, widget_selector):
            pacer.pause(0.8, 1.2)
            print("[jd-login] 验证码浮层已出现", flush=True)
            return True
        try:
            snippet = page.evaluate(
                "() => (document.body.innerText || '').replace(/\\s+/g,' ').slice(0, 160)"
            )
            if snippet and snippet != last_hint:
                print(f"[jd-login] 等待浮层… page_text={snippet!r}", flush=True)
                last_hint = snippet
        except Exception:
            pass
        pacer.pause(0.5, 0.9)
    print("[jd-login] 超时：未检测到验证码浮层", flush=True)
    return False


def solve_jd_login_captcha(
    page,
    platform,
    widget_selector=None,
    auto_trigger=True,
    login_user=None,
    login_pass=None,
    track_captcha_type=None,
    rotate_captcha_type=None,
    slide_captcha_type=None,
    track_width=300.0,
    full_angle=360.0,
    max_rounds=3,
    humanize_factor=1.3,
):
    """
    京东登录验证码自动识别 + 求解：track / rotate / slide 三路分发。
    """
    widget_sel = widget_selector or DEFAULT_WIDGET
    pacer = HumanPacer(humanize_factor)
    install_jd_jcap_hook(page)
    panel_seen = False

    if auto_trigger and login_user and login_pass:
        if not trigger_jd_pwd_login(page, login_user, login_pass, pacer):
            return {
                "ok": False,
                "panel_seen": False,
                "category": "unknown",
                "detection": {},
                "rounds": 0,
                "last_error": "自动填表/点击登录失败，请检查选择器或改用 --no-auto-trigger",
            }
    elif auto_trigger:
        return {
            "ok": False,
            "panel_seen": False,
            "category": "unknown",
            "detection": {},
            "rounds": 0,
            "last_error": "缺少登录凭据；请设 JD_LOGIN_USER/JD_LOGIN_PASS 或 --no-auto-trigger",
        }

    panel_seen = wait_jd_captcha_panel(page, widget_sel, pacer=pacer)
    if not panel_seen:
        return {
            "ok": False,
            "panel_seen": False,
            "category": "unknown",
            "detection": {},
            "rounds": 0,
            "last_error": "未出现验证码浮层（可能未触发风控、账号错误，或浮层加载慢于 40s）",
        }

    detection = detect_captcha_category(page, widget_sel)
    category = detection.get("category") or "unknown"
    print(f"[jd-login] 类型识别: {format_detection_log(detection)}", flush=True)

    if category == "unknown":
        pacer.pause(1.5, 2.0)
        detection = detect_captcha_category(page, widget_sel)
        category = detection.get("category") or "unknown"
        print(f"[jd-login] 二次识别: {format_detection_log(detection)}", flush=True)

    img_sel = detection.get("img_selector") or ".captcha_body .slot-content img, .JDJRV-bigimg img"
    handle_sel = detection.get("handle_selector") or "#slider-div, .JDJRV-slide-btn, .JDJRV-slide-inner"

    bingtop_type = resolve_captcha_type(
        category,
        track=track_captcha_type,
        rotate=rotate_captcha_type,
        slide=slide_captcha_type,
    )
    if bingtop_type:
        label = CATEGORY_TYPE_LABEL.get(category, category)
        print(
            f"[jd-login] 识别={category} → BingTop captchaType={bingtop_type} ({label})",
            flush=True,
        )
    detection["bingtop_captcha_type"] = bingtop_type

    if category == "track":
        res = solve_track_draw(
            page,
            platform,
            captcha_img_selector=img_sel,
            captcha_type=bingtop_type,
            widget_selector=widget_sel,
            max_rounds=max_rounds,
            humanize_factor=humanize_factor,
            wait_visible=False,
        )
        ok = bool(res.get("ok")) or is_jd_captcha_success(page, widget_sel, challenge_seen=True)
        return {
            "ok": ok,
            "panel_seen": True,
            "category": "track",
            "detection": detection,
            "rounds": res.get("rounds", 0),
            "points": res.get("points", []),
            "captcha_type": res.get("captcha_type"),
            "last_error": res.get("last_error"),
        }

    if category == "rotate":
        rotate_track = measure_jd_rotate_track_width(page) or track_width
        res = solve_rotate_captcha(
            page,
            platform,
            captcha_img_selector=img_sel,
            handle_selector=handle_sel,
            captcha_type=bingtop_type,
            widget_selector=widget_sel,
            track_width=rotate_track,
            full_angle=full_angle,
            max_rounds=max_rounds,
            humanize_factor=humanize_factor,
            wait_visible=False,
        )
        ok = bool(res.get("ok")) or is_jd_captcha_success(page, widget_sel, challenge_seen=True)
        return {
            "ok": ok,
            "panel_seen": True,
            "category": "rotate",
            "detection": detection,
            "rounds": res.get("rounds", 0),
            "angle": res.get("angle", 0),
            "captcha_type": res.get("captcha_type"),
            "last_error": res.get("last_error"),
        }

    if category == "slide":
        res = solve_jd_jcap_slide(
            page,
            platform,
            captcha_type=bingtop_type,
            widget_selector=widget_sel,
            auto_trigger=False,
            max_rounds=max_rounds,
            humanize_factor=humanize_factor,
        )
        ok = bool(res.get("ok")) or is_jd_captcha_success(page, widget_sel, challenge_seen=True)
        return {
            "ok": ok,
            "panel_seen": True,
            "category": "slide",
            "detection": detection,
            "rounds": res.get("rounds", 0),
            "offset": res.get("offset", 0),
            "last_error": res.get("last_error"),
        }

    return {
        "ok": False,
        "panel_seen": True,
        "category": category,
        "detection": detection,
        "rounds": 0,
        "last_error": f"浮层已出现但无法识别类型（hint={detection.get('hint_text', '')[:80]}）",
    }
