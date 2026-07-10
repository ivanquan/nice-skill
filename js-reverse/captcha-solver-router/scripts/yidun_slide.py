#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网易易盾滑动拼图验证码：识别缺口 + 拟人拖拽（通用 R2 流程）。"""

import base64
import random
import re
import time
import urllib.request

from browser_stealth import get_mouse_state, human_slide_drag
from recaptcha_grid import HumanPacer
from yidun_click import (
    find_yidun_widget,
    get_yidun_slide_urls_from_network,
    install_yidun_front_hook,
    is_yidun_success,
    trigger_yidun,
    _log_stealth_status,
)

from bingtop_types import SLIDE_1310, normalize_slide_types

DEFAULT_SLIDE_TYPE = {
    "bingtop": SLIDE_1310,
    "jfbym": 20111,
}

YIDUN_SLIDER_SELECTORS = [
    ".yidun_slider",
    ".yidun_slider__icon",
    ".yidun_jigsaw__slider",
]
YIDUN_BG_SELECTORS = [".yidun_bgimg img", ".yidun_bgimg"]
YIDUN_SLICE_SELECTORS = [".yidun_jigsaw img", ".yidun_jigsaw"]


def yidun_slide_panel_visible(page, widget_selector=None):
    """判断易盾滑块拼图面板是否已展开。"""
    root = find_yidun_widget(page, widget_selector)
    if not root:
        return False
    try:
        slider = root.locator(".yidun_slider, .yidun_jigsaw").first
        bg = root.locator(".yidun_bgimg img, .yidun_bgimg").first
        return slider.count() and bg.count() and slider.is_visible() and bg.is_visible()
    except Exception:
        return False


def wait_yidun_network_images(page, timeout_sec=10, pacer=None):
    """等待 get 接口返回 bg + front(拼图块) URL。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        bg, sl = get_yidun_slide_urls_from_network(page)
        if bg and sl:
            return True
        pacer.pause(0.35, 0.55)
    bg, sl = get_yidun_slide_urls_from_network(page)
    return bool(bg and sl)


def wait_yidun_slide_ready(page, timeout_sec=15, pacer=None, widget_selector=None):
    """等待滑块面板与拼图图片加载完成。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if yidun_slide_panel_visible(page, widget_selector):
            bg, sl = get_yidun_slide_urls_from_network(page)
            if bg and sl:
                return True
            root = find_yidun_widget(page, widget_selector)
            if root:
                try:
                    bimg = root.locator(".yidun_bgimg img[src^='http']").first
                    simg = root.locator(".yidun_jigsaw img[src^='http']").first
                    if bimg.count() and simg.count():
                        return True
                except Exception:
                    pass
        pacer.pause(0.4, 0.75)
    return yidun_slide_panel_visible(page, widget_selector)


def _download_image_b64(url):
    """下载图片 URL 为 base64。"""
    req = urllib.request.Request(
        url,
        headers={"Referer": "https://dun.163.com/", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    if len(raw) < 500:
        raise RuntimeError(f"图片过小: {len(raw)} bytes")
    return base64.b64encode(raw).decode("ascii")


def _element_img_b64(loc):
    """从元素 src 下载或截图获取 base64。"""
    tag = (loc.evaluate("el => el.tagName") or "").upper()
    if tag == "IMG":
        src = loc.get_attribute("src") or ""
        if src.startswith("http"):
            return _download_image_b64(src)
    png = loc.screenshot(timeout=10000)
    return base64.b64encode(png).decode("ascii")


def capture_yidun_slide_images(page, widget_selector=None):
    """获取易盾滑块 bg + slice 的 base64，返回 (bg_b64, slice_b64)。"""
    wait_yidun_network_images(page, timeout_sec=12)
    bg_url, slice_url = get_yidun_slide_urls_from_network(page)
    if bg_url and slice_url:
        print(f"[yidun-slide] 网络下载 bg+slice", flush=True)
        return _download_image_b64(bg_url), _download_image_b64(slice_url)

    root = find_yidun_widget(page, widget_selector)
    if not root:
        raise RuntimeError("未找到易盾 widget")
    bg_loc = None
    slice_loc = None
    for sel in YIDUN_BG_SELECTORS:
        loc = root.locator(sel).first
        if loc.count() and loc.is_visible():
            bg_loc = loc
            break
    for sel in YIDUN_SLICE_SELECTORS:
        loc = root.locator(sel).first
        if loc.count() and loc.is_visible():
            slice_loc = loc
            break
    if not bg_loc or not slice_loc:
        raise RuntimeError("未找到滑块背景图或拼图块元素")
    bg_b64 = _element_img_b64(bg_loc)
    slice_b64 = _element_img_b64(slice_loc)
    print(f"[yidun-slide] DOM 获取 bg+slice ok", flush=True)
    return bg_b64, slice_b64


def load_slide_solver(platform):
    """加载打码平台适配器。"""
    from yidun_click import load_click_solver

    return load_click_solver(platform)


def classify_yidun_slide(platform, bg_b64, slice_b64, captcha_type=None):
    """调用打码平台识别滑块距离。"""
    solver = load_slide_solver(platform)
    ctype = captcha_type or DEFAULT_SLIDE_TYPE.get(platform)
    if ctype is None:
        raise RuntimeError(f"平台 {platform} 未配置默认 slide captcha_type")
    if platform == "bingtop":
        types_to_try = normalize_slide_types(ctype)
    else:
        types_to_try = [ctype]
    last_exc = None
    for t in types_to_try:
        try:
            print(f"[slide] 请求 BingTop captchaType={t}（官方滑块类 1310/1318）", flush=True)
            return solver.solve_slide(bg_b64=bg_b64, slice_b64=slice_b64, captcha_type=t)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "type error" in msg or "captcha type" in msg:
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("滑块识别失败")


def parse_slide_offset(raw):
    """解析打码平台返回的滑动距离（像素）。"""
    if raw is None:
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, dict):
        for k in ("x", "X", "offset", "distance"):
            if k in raw and raw[k] is not None:
                return int(float(raw[k]))
        data = raw.get("data") or raw.get("recognition")
        if data is not None:
            return parse_slide_offset(data)
    text = str(raw).strip()
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    if nums:
        return int(float(nums[0]))
    return 0


def locate_slider_handle(page, widget_selector=None):
    """定位滑块拖拽手柄元素。"""
    root = find_yidun_widget(page, widget_selector)
    scope = root if root else page
    for sel in YIDUN_SLIDER_SELECTORS:
        loc = scope.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    return loc, sel
            except Exception:
                continue
    raise RuntimeError("未找到易盾滑块手柄")


def measure_yidun_slide_geometry(page, widget_selector=None):
    """
    读取易盾滑块几何参数：背景/拼图块原图尺寸、轨道宽度、手柄宽度。
    用于将打码平台返回的缺口坐标换算为实际拖拽像素。
    """
    root = find_yidun_widget(page, widget_selector)
    if not root:
        return None
    try:
        geom = root.evaluate(
            """(el) => {
                const bg = el.querySelector('.yidun_bgimg img, .yidun_bg-img, .yidun_bgimg');
                const slice = el.querySelector('.yidun_jigsaw img, .yidun_jigsaw');
                const control = el.querySelector('.yidun_control');
                const handle = el.querySelector('.yidun_slider');
                const br = bg ? bg.getBoundingClientRect() : {};
                const sr = slice ? slice.getBoundingClientRect() : {};
                const cr = control ? control.getBoundingClientRect() : {};
                const hr = handle ? handle.getBoundingClientRect() : {};
                return {
                    bgNaturalW: bg ? (bg.naturalWidth || bg.width || 320) : 320,
                    bgDisplayW: br.width || 320,
                    sliceNaturalW: slice ? (slice.naturalWidth || slice.width || 60) : 60,
                    sliceDisplayW: sr.width || 0,
                    trackW: cr.width || 320,
                    handleW: hr.width || 40,
                };
            }"""
        )
        return geom
    except Exception:
        return None


# 冰拓双图返回值到轨道拖拽的标定偏置（实测系统性偏右约 3~5px）
SLIDE_CALIB_BIAS = (3.0, 5.5)


def calc_slide_drag_distance(gap_x_logic, geom):
    """
    将打码平台返回的缺口 X（基于 bg 原图像素）换算为轨道上的拖拽距离。

    算法说明（冰拓 1310 双图）：
    1. 返回值 = 拼图块左缘在 bg 原图上的目标 X；
    2. bg 可移动区间 = bg_w - slice_w，轨道可移动区间 = track_w - handle_w；
    3. 两区间按比例映射得到基础拖拽距；
    4. 扣减 SLIDE_CALIB_BIAS（3~5px）修正实测系统性偏右，不再做正向补偿。
    """
    if not geom:
        return max(5.0, float(gap_x_logic) - random.uniform(*SLIDE_CALIB_BIAS))

    bg_w = float(geom.get("bgNaturalW") or 320)
    slice_w = float(geom.get("sliceNaturalW") or 60)
    track_w = float(geom.get("trackW") or 320)
    handle_w = float(geom.get("handleW") or 40)

    bg_travel = max(bg_w - slice_w, 1.0)
    track_travel = max(track_w - handle_w, 1.0)
    gap = max(0.0, min(float(gap_x_logic), bg_travel))

    drag = gap * track_travel / bg_travel

    calib = random.uniform(*SLIDE_CALIB_BIAS)
    jitter = random.uniform(-0.5, 0.5)
    drag = drag - calib + jitter
    drag = max(5.0, drag)

    print(
        f"[yidun-slide] 距离换算 gap={gap_x_logic} bg={bg_w:.0f} slice={slice_w:.0f} "
        f"track={track_w:.0f} handle={handle_w:.0f} calib=-{calib:.1f} -> drag={drag:.1f}",
        flush=True,
    )
    return drag


def scale_slide_offset(page, offset_logic, widget_selector=None):
    """将原图识别距离换算为滑块轨道上的拖拽距离（含拼图块尺寸修正）。"""
    geom = measure_yidun_slide_geometry(page, widget_selector)
    return calc_slide_drag_distance(offset_logic, geom)


def drag_yidun_slider(page, offset_px, widget_selector=None, pacer=None):
    """拟人拖拽易盾滑块手柄。"""
    if pacer is None:
        pacer = HumanPacer()
    handle, sel = locate_slider_handle(page, widget_selector)
    box = handle.bounding_box()
    if not box:
        raise RuntimeError(f"无法获取滑块手柄位置: {sel}")
    sx = box["x"] + box["width"] / 2
    sy = box["y"] + box["height"] / 2
    tx = sx + float(offset_px)
    print(f"[yidun-slide] 拖拽 {sel} offset={offset_px:.1f}px", flush=True)
    pacer.pause(0.5, 1.0)
    human_slide_drag(page, sx, sy, tx, sy, state=get_mouse_state(page), accurate=True)


def solve_yidun_slide(
    page,
    platform,
    captcha_type=None,
    widget_selector=None,
    auto_trigger=True,
    max_rounds=3,
    humanize_factor=1.3,
):
    """
    通用易盾滑动拼图流程：触发面板 → 识别缺口 → 拟人拖拽。
    """
    pacer = HumanPacer(humanize_factor)
    last_error = None
    install_yidun_front_hook(page)
    _log_stealth_status(page)

    if auto_trigger:
        if not trigger_yidun(page, pacer, widget_selector):
            return {
                "ok": False,
                "rounds": 0,
                "offset": 0,
                "last_error": "页面上未找到易盾验证码 widget",
            }
        if not wait_yidun_slide_ready(page, pacer=pacer, widget_selector=widget_selector):
            return {
                "ok": False,
                "rounds": 0,
                "offset": 0,
                "last_error": "点击后未出现滑块拼图面板",
            }
        wait_yidun_network_images(page, timeout_sec=12, pacer=pacer)

    rounds = 0
    while rounds < max_rounds:
        if is_yidun_success(page, widget_selector):
            return {"ok": True, "rounds": rounds, "offset": 0, "last_error": None}

        if not yidun_slide_panel_visible(page, widget_selector):
            if auto_trigger and rounds == 0:
                trigger_yidun(page, pacer, widget_selector)
                wait_yidun_slide_ready(page, pacer=pacer, widget_selector=widget_selector)
            if not yidun_slide_panel_visible(page, widget_selector):
                last_error = "滑块面板不可见"
                break

        pacer.pause(0.5, 1.0)
        wait_yidun_network_images(page, timeout_sec=10, pacer=pacer)
        try:
            bg_b64, slice_b64 = capture_yidun_slide_images(page, widget_selector)
        except Exception as exc:
            last_error = f"获取滑块图片失败: {exc}"
            rounds += 1
            pacer.pause(1.0, 1.5)
            continue

        raw = None
        try:
            raw = classify_yidun_slide(platform, bg_b64, slice_b64, captcha_type=captcha_type)
            offset_logic = parse_slide_offset(raw)
        except Exception as exc:
            last_error = f"平台识别失败: {exc}"
            print(f"[yidun-slide] 识别异常: {exc}", flush=True)
            rounds += 1
            pacer.pause(1.5, 2.5)
            continue

        if offset_logic <= 0:
            last_error = f"平台未返回有效距离: {raw!r}"
            rounds += 1
            continue

        offset_px = scale_slide_offset(page, offset_logic, widget_selector)
        print(f"[yidun-slide] 第 {rounds + 1} 轮: logic={offset_logic} drag={offset_px:.1f}", flush=True)

        try:
            drag_yidun_slider(page, offset_px, widget_selector, pacer)
        except Exception as exc:
            last_error = f"拖拽失败: {exc}"
            rounds += 1
            continue

        pacer.pause(2.0, 3.5)
        for _ in range(4):
            if is_yidun_success(page, widget_selector):
                rounds += 1
                return {
                    "ok": True,
                    "rounds": rounds,
                    "offset": offset_logic,
                    "last_error": None,
                }
            pacer.pause(0.7, 1.2)
        rounds += 1
        last_error = "拖拽完成但未检测到验证成功"

    return {
        "ok": is_yidun_success(page, widget_selector),
        "rounds": rounds,
        "offset": 0,
        "last_error": last_error,
    }
