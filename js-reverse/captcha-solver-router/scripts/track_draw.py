#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用轨迹绘制验证码 R2：截图 → 打码平台识别路径点 → 拟人回放绘制。

适用于「请按照图中轨迹绘制」等 gesture/track 类验证码（京东 JCAP、顶象等）。
"""

import base64
import io
import re
import time

from browser_stealth import get_mouse_state, human_path_draw
from recaptcha_grid import HumanPacer
from yidun_click import load_click_solver, parse_click_coords

from bingtop_types import TRACK_3002, normalize_track_types

DEFAULT_TRACK_TYPE = {"bingtop": TRACK_3002}


def _png_dims(png_bytes):
    """从 PNG 字节读取宽高。"""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        return float(img.size[0]), float(img.size[1])
    except Exception:
        return 0.0, 0.0


def capture_captcha_element(page, img_selector):
    """
    截取验证码绘制区域，返回 (b64, box, coord_w, coord_h)。
    coord 为送给打码平台的图片像素尺寸（截图或原图 natural 尺寸）。
    """
    loc = page.locator(img_selector).first
    if not loc.count():
        raise RuntimeError(f"未找到验证码区域: {img_selector}")
    loc.wait_for(state="visible", timeout=15000)
    box = loc.bounding_box()
    if not box:
        raise RuntimeError(f"无法获取元素位置: {img_selector}")

    tag = (loc.evaluate("el => el.tagName") or "").upper()
    if tag == "IMG":
        src = loc.get_attribute("src") or ""
        if src.startswith("data:image") and "," in src:
            b64 = src.split(",", 1)[1]
            raw = base64.b64decode(b64)
            cw, ch = _png_dims(raw)
            if cw and ch:
                print(f"[track] data-uri 图片 {cw:.0f}x{ch:.0f}", flush=True)
                return b64, box, cw, ch
        natural = loc.evaluate(
            """(el) => ({
                w: el.naturalWidth || el.clientWidth || el.width || 0,
                h: el.naturalHeight || el.clientHeight || el.height || 0,
            })"""
        )
        nw = float(natural.get("w") or 0)
        nh = float(natural.get("h") or 0)
        if nw > 10 and nh > 10:
            if src.startswith("http"):
                from yidun_slide import _download_image_b64
                b64 = _download_image_b64(src)
                print(f"[track] 网络下载图片 {nw:.0f}x{nh:.0f}", flush=True)
                return b64, box, nw, nh
            png = loc.screenshot(timeout=10000)
            b64 = base64.b64encode(png).decode("ascii")
            cw, ch = _png_dims(png)
            coord_w = cw or nw or box["width"]
            coord_h = ch or nh or box["height"]
            print(f"[track] IMG 截图 {coord_w:.0f}x{coord_h:.0f}", flush=True)
            return b64, box, coord_w, coord_h

    png = loc.screenshot(timeout=10000)
    b64 = base64.b64encode(png).decode("ascii")
    cw, ch = _png_dims(png)
    coord_w = cw or box["width"]
    coord_h = ch or box["height"]
    print(f"[track] 元素截图 {coord_w:.0f}x{coord_h:.0f} sel={img_selector}", flush=True)
    return b64, box, coord_w, coord_h


def scale_track_points(logic_points, box, coord_w, coord_h):
    """将打码平台逻辑坐标换算为页面绝对坐标。"""
    if not logic_points:
        return []
    cw = float(coord_w or box["width"] or 1)
    ch = float(coord_h or box["height"] or 1)
    sx = float(box["width"]) / cw
    sy = float(box["height"]) / ch
    ox, oy = float(box["x"]), float(box["y"])
    out = []
    for x, y in logic_points:
        out.append((ox + float(x) * sx, oy + float(y) * sy))
    return out


def classify_track(platform, image_b64, captcha_type=None):
    """调用打码平台识别轨迹坐标序列。"""
    solver = load_click_solver(platform)
    ctype = captcha_type or TRACK_3002
    if platform != "bingtop":
        ctype = captcha_type or DEFAULT_TRACK_TYPE.get(platform)
        if ctype is None:
            raise RuntimeError(f"平台 {platform} 未配置默认 track captcha_type")
        types_to_try = [ctype]
    else:
        types_to_try = normalize_track_types(ctype)

    last_exc = None
    for t in types_to_try:
        try:
            print(f"[track] 请求 BingTop captchaType={t}（轨迹类 3002）", flush=True)
            if hasattr(solver, "solve_track"):
                raw = solver.solve_track(b64=image_b64, captcha_type=t)
            else:
                raw = solver.solve("track", b64=image_b64, captcha_type=t)
            return raw, t
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "type error" in msg or "captcha type" in msg or "404" in msg:
                print(f"[track] BingTop type={t} 不可用: {exc}", flush=True)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("轨迹识别失败")


def parse_track_points(raw):
    """解析打码平台返回的轨迹点列表。"""
    return parse_click_coords(raw)


def is_track_panel_visible(page, img_selector, widget_selector=None):
    """判断轨迹验证码绘制区域是否仍可见。"""
    selectors = [s.strip() for s in (widget_selector or "").split(",") if s.strip()]
    selectors.append(img_selector)
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    return True
            except Exception:
                return True
    return False


def is_track_success(page, img_selector, widget_selector=None, success_selector=None):
    """检测轨迹验证是否通过（面板消失或成功选择器出现）。"""
    if success_selector:
        loc = page.locator(success_selector).first
        if loc.count():
            try:
                if loc.is_visible():
                    return True
            except Exception:
                return True
    err = page.locator(".JDJRV-error, .jdcap-error, .captcha-error, [class*='error']").first
    if err.count():
        try:
            if err.is_visible():
                return False
        except Exception:
            pass
    return not is_track_panel_visible(page, img_selector, widget_selector)


def replay_track(page, abs_points, pacer=None):
    """在页面上拟人回放轨迹绘制。"""
    if pacer is None:
        pacer = HumanPacer()
    human_path_draw(page, abs_points, state=get_mouse_state(page), interpolate=True)
    pacer.pause(0.3, 0.6)


def solve_track_draw(
    page,
    platform,
    captcha_img_selector,
    captcha_type=None,
    widget_selector=None,
    success_selector=None,
    max_rounds=3,
    humanize_factor=1.3,
    wait_visible=True,
):
    """
    通用轨迹绘制 R2：截图识别 → 坐标换算 → 拟人绘制 → 检测结果。
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
                "points": [],
                "captcha_type": captcha_type,
                "last_error": f"验证码区域不可见: {exc}",
            }

    rounds = 0
    while rounds < max_rounds:
        if is_track_success(page, captcha_img_selector, widget_selector, success_selector):
            return {
                "ok": True,
                "rounds": rounds,
                "points": [],
                "captcha_type": captcha_type,
                "last_error": None,
            }

        if not is_track_panel_visible(page, captcha_img_selector, widget_selector):
            last_error = "轨迹验证码区域不可见"
            break

        pacer.pause(0.4, 0.8)
        try:
            b64, box, coord_w, coord_h = capture_captcha_element(page, captcha_img_selector)
        except Exception as exc:
            last_error = f"截图失败: {exc}"
            rounds += 1
            pacer.pause(1.0, 1.5)
            continue

        try:
            raw, used_type = classify_track(platform, b64, captcha_type=captcha_type)
            logic_pts = parse_track_points(raw)
            captcha_type = used_type
        except Exception as exc:
            last_error = f"平台识别失败: {exc}"
            print(f"[track] 识别异常: {exc}", flush=True)
            rounds += 1
            pacer.pause(1.5, 2.5)
            continue

        if len(logic_pts) < 2:
            last_error = f"平台未返回有效轨迹点: {raw!r}"
            rounds += 1
            continue

        abs_pts = scale_track_points(logic_pts, box, coord_w, coord_h)
        print(
            f"[track] 第 {rounds + 1} 轮: type={used_type} logic={len(logic_pts)}pts "
            f"scale={coord_w:.0f}x{coord_h:.0f}→{box['width']:.0f}x{box['height']:.0f}",
            flush=True,
        )

        try:
            replay_track(page, abs_pts, pacer)
        except Exception as exc:
            last_error = f"轨迹回放失败: {exc}"
            rounds += 1
            continue

        pacer.pause(1.5, 2.5)
        for _ in range(5):
            if is_track_success(page, captcha_img_selector, widget_selector, success_selector):
                rounds += 1
                return {
                    "ok": True,
                    "rounds": rounds,
                    "points": logic_pts,
                    "captcha_type": used_type,
                    "last_error": None,
                }
            pacer.pause(0.6, 1.0)
        rounds += 1
        last_error = "绘制完成但未检测到验证成功"

    return {
        "ok": is_track_success(page, captcha_img_selector, widget_selector, success_selector),
        "rounds": rounds,
        "points": [],
        "captcha_type": captcha_type,
        "last_error": last_error,
    }
