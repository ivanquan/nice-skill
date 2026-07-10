#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用旋转验证码 R2：截图 → 打码平台识别角度 → 换算水平位移 → 拟人拖拽手柄。
"""

import re

from browser_stealth import get_mouse_state, human_slide_drag
from recaptcha_grid import HumanPacer
from track_draw import capture_captcha_element, is_track_panel_visible
from yidun_click import load_click_solver

from bingtop_types import ROTATE_11201, normalize_rotate_types

_MEASURE_ROTATE_JS = """
(handleSels) => {
    const track = document.querySelector(
        '.captcha_footer .drag-box, #local_footer .drag-box, .drag-box, .JDJRV-slide-bg, .JDJRV-slide'
    );
    const selectors = (handleSels || '').split(',').map(s => s.trim()).filter(Boolean);
    let handle = null;
    for (const s of selectors) {
        const el = document.querySelector(s);
        if (el) { handle = el; break; }
    }
    const tr = track ? track.getBoundingClientRect() : {};
    const hr = handle ? handle.getBoundingClientRect() : {};
    const trackW = tr.width || 0;
    const handleW = hr.width || 48;
    return {
        trackW: trackW,
        handleW: handleW,
        effectiveW: Math.max(trackW - handleW, 40),
        trackX: tr.x || 0,
        trackY: tr.y + tr.height / 2,
        handleX: hr.x || 0,
        handleY: hr.y + hr.height / 2,
        hasTrack: !!(track && trackW > 20),
    };
}
"""


def parse_rotate_angle(raw):
    """解析打码平台返回的旋转角度（度）。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    if nums:
        return float(nums[0])
    return None


def normalize_rotate_angle(angle):
    """将角度归一化到 (-180, 180] 区间。"""
    a = float(angle) % 360.0
    if a > 180.0:
        a -= 360.0
    return a


def classify_rotate(platform, image_b64, captcha_type=None):
    """调用打码平台识别旋转角度。"""
    solver = load_click_solver(platform)
    if platform == "bingtop":
        types_to_try = normalize_rotate_types(captcha_type)
    else:
        ctype = captcha_type or ROTATE_11201
        types_to_try = [ctype]

    last_exc = None
    for t in types_to_try:
        try:
            print(
                f"[rotate-captcha] 请求 BingTop captchaType={t}（官方旋转类 11201/1120）",
                flush=True,
            )
            raw = solver.solve_rotate(b64=image_b64, captcha_type=t)
            return raw, t
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "type error" in msg or "captcha type" in msg or "404" in msg:
                print(f"[rotate-captcha] BingTop type={t} 不可用: {exc}", flush=True)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("旋转识别失败")


def measure_rotate_geometry(page, handle_selector):
    """读取旋转滑轨与手柄几何参数（有效拖拽宽度 = 轨道宽 - 手柄宽）。"""
    try:
        geom = page.evaluate(_MEASURE_ROTATE_JS, handle_selector)
        if geom and geom.get("hasTrack"):
            return geom
    except Exception:
        pass
    loc = page.locator(handle_selector.split(",")[0].strip()).first
    if loc.count():
        box = loc.bounding_box()
        if box:
            hw = box["width"]
            return {
                "trackW": 290.0,
                "handleW": hw,
                "effectiveW": max(290.0 - hw, 40),
                "trackX": box["x"] - 2,
                "trackY": box["y"] + box["height"] / 2,
                "handleX": box["x"],
                "handleY": box["y"] + box["height"] / 2,
                "hasTrack": False,
            }
    return {
        "trackW": 290.0,
        "handleW": 48.0,
        "effectiveW": 242.0,
        "trackX": 0,
        "trackY": 0,
        "handleX": 0,
        "handleY": 0,
        "hasTrack": False,
    }


def calc_rotate_drag_px(angle, effective_width, full_angle=360.0):
    """将旋转角度换算为滑轨有效行程上的水平位移像素。"""
    a = normalize_rotate_angle(angle)
    return float(effective_width) * a / float(full_angle)


def refresh_rotate_captcha(page, pacer=None):
    """失败后刷新旋转验证码，重置滑块与题面。"""
    if pacer is None:
        pacer = HumanPacer()
    for sel in (
        ".jcap_refresh",
        "#refreshPng",
        ".captcha_header .jcap_refresh",
        ".JDJRV-refresh",
    ):
        loc = page.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    loc.click(timeout=5000)
                    print("[rotate-captcha] 已点击刷新，重置滑块", flush=True)
                    pacer.pause(1.2, 2.0)
                    return True
            except Exception:
                continue
    return False


def is_rotate_success(page, img_selector, widget_selector=None, success_selector=None):
    """检测旋转验证是否通过。"""
    if success_selector:
        loc = page.locator(success_selector).first
        if loc.count():
            try:
                if loc.is_visible():
                    return True
            except Exception:
                return True
    err = page.locator(
        ".JDJRV-error, .jdcap-error, .captcha-error, .img_tips, [class*='error']"
    ).first
    if err.count():
        try:
            if err.is_visible():
                txt = (err.inner_text(timeout=300) or "").strip()
                if txt and "成功" not in txt:
                    return False
        except Exception:
            pass
    modal = page.locator("#captcha_modal, .captcha_modal_pc").first
    if modal.count():
        try:
            if not modal.is_visible():
                return True
        except Exception:
            return True
    return not is_track_panel_visible(page, img_selector, widget_selector)


def drag_rotate_handle(page, handle_selector, angle, track_width=300.0, full_angle=360.0):
    """
    按角度拟人拖拽旋转手柄：从滑轨起点拖到目标位置（非累加偏移）。
    使用 human_slide_drag(accurate=True) 以触发京东等站点的 pointer 监听。
    """
    geom = measure_rotate_geometry(page, handle_selector)
    effective_w = geom.get("effectiveW") or max(float(track_width) - geom.get("handleW", 48), 40)
    offset = calc_rotate_drag_px(angle, effective_w, full_angle)
    handle_w = geom.get("handleW") or 48

    if geom.get("hasTrack"):
        sx = geom["trackX"] + handle_w / 2
        sy = geom.get("trackY") or geom.get("handleY")
        tx = geom["trackX"] + offset + handle_w / 2
        max_tx = geom["trackX"] + geom["trackW"] - handle_w / 2
        min_tx = geom["trackX"] + handle_w / 2
        tx = max(min_tx, min(tx, max_tx))
    else:
        loc = page.locator(handle_selector.split(",")[0].strip()).first
        if not loc.count():
            raise RuntimeError(f"未找到旋转手柄: {handle_selector}")
        box = loc.bounding_box()
        if not box:
            raise RuntimeError(f"无法获取手柄位置: {handle_selector}")
        sx = box["x"] + box["width"] / 2
        sy = box["y"] + box["height"] / 2
        tx = sx + offset

    state = get_mouse_state(page)
    human_slide_drag(page, sx, sy, tx, sy, state=state, allow_overshoot=False, accurate=True)
    print(
        f"[rotate-captcha] 拖拽 angle={normalize_rotate_angle(angle):.1f}° "
        f"offset={offset:.1f}px effective={effective_w:.0f} "
        f"({sx:.0f},{sy:.0f})→({tx:.0f},{sy:.0f})",
        flush=True,
    )


def solve_rotate_captcha(
    page,
    platform,
    captcha_img_selector,
    handle_selector,
    captcha_type=None,
    widget_selector=None,
    success_selector=None,
    track_width=300.0,
    full_angle=360.0,
    max_rounds=3,
    humanize_factor=1.3,
    wait_visible=True,
):
    """
    通用旋转验证码 R2：截图识别角度 → 换算位移 → 拟人拖拽 → 检测结果。
    """
    pacer = HumanPacer(humanize_factor)
    last_error = None

    if wait_visible:
        try:
            page.wait_for_selector(captcha_img_selector, state="visible", timeout=30000)
            pacer.pause(0.5, 1.0)
        except Exception as exc:
            return {
                "ok": False,
                "rounds": 0,
                "angle": 0,
                "captcha_type": captcha_type,
                "last_error": f"验证码区域不可见: {exc}",
            }

    rounds = 0
    while rounds < max_rounds:
        if is_rotate_success(page, captcha_img_selector, widget_selector, success_selector):
            return {
                "ok": True,
                "rounds": rounds,
                "angle": 0,
                "captcha_type": captcha_type,
                "last_error": None,
            }

        if not is_track_panel_visible(page, captcha_img_selector, widget_selector):
            last_error = "旋转验证码区域不可见"
            break

        # 上一轮拖拽失败后刷新题面，避免滑块停在中间导致角度累加错乱
        if rounds > 0:
            refresh_rotate_captcha(page, pacer)

        pacer.pause(0.4, 0.8)
        try:
            b64, _box, _cw, _ch = capture_captcha_element(page, captcha_img_selector)
        except Exception as exc:
            last_error = f"截图失败: {exc}"
            rounds += 1
            pacer.pause(1.0, 1.5)
            continue

        try:
            raw, used_type = classify_rotate(platform, b64, captcha_type=captcha_type)
            angle = parse_rotate_angle(raw)
            captcha_type = used_type
        except Exception as exc:
            last_error = f"平台识别失败: {exc}"
            print(f"[rotate-captcha] 识别异常: {exc}", flush=True)
            rounds += 1
            pacer.pause(1.5, 2.5)
            continue

        if angle is None:
            last_error = f"平台未返回有效角度: {raw!r}"
            rounds += 1
            continue

        print(f"[rotate-captcha] 第 {rounds + 1} 轮: type={used_type} angle={angle:.1f}° raw={raw!r}", flush=True)

        try:
            drag_rotate_handle(
                page,
                handle_selector,
                angle,
                track_width=track_width,
                full_angle=full_angle,
            )
        except Exception as exc:
            last_error = f"拖拽失败: {exc}"
            rounds += 1
            continue

        pacer.pause(1.8, 3.0)
        for _ in range(6):
            if is_rotate_success(page, captcha_img_selector, widget_selector, success_selector):
                rounds += 1
                return {
                    "ok": True,
                    "rounds": rounds,
                    "angle": angle,
                    "captcha_type": used_type,
                    "last_error": None,
                }
            pacer.pause(0.6, 1.0)
        rounds += 1
        last_error = "拖拽完成但未检测到验证成功"

    return {
        "ok": is_rotate_success(page, captcha_img_selector, widget_selector, success_selector),
        "rounds": rounds,
        "angle": 0,
        "captcha_type": captcha_type,
        "last_error": last_error,
    }
