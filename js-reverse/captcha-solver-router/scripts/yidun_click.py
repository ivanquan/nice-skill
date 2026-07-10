#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网易易盾文字点选验证码：识别题面 + 拟人点击（通用 R2 流程）。"""

import base64
import json
import random
import re
import time

from recaptcha_grid import HumanPacer
from browser_stealth import get_mouse_state, human_click_at

# 各平台文字点选默认 captchaType（可被 CLI 覆盖）
DEFAULT_CLICK_TYPE = {
    "bingtop": 13152,
    "jfbym": 30100,
}

# 冰拓文字点选备选类型（账号未开通时依次尝试）
BINGTOP_CLICK_FALLBACK = [13152, 1315, 1324, 13242]

# 题面模板用字（非点击目标）
INSTRUCTION_NOISE = set("请依次点击选点图块片中的验证刷新切换语音")

YIDUN_IMG_SELECTORS = [
    ".yidun_bgimg img",
    ".yidun_bgimg",
    ".yidun_jigsaw img",
]
YIDUN_TIP_SELECTORS = [
    ".yidun_tips__text",
    ".yidun_top__bar",
    ".yidun_tips",
]
YIDUN_TARGET_SELECTORS = [
    ".yidun_tips__point",
    ".yidun_tips__answer",
]
YIDUN_CLICK_AREA_SELECTORS = [
    ".yidun_bgimg",
    ".yidun_bgimg img",
    ".yidun_jigsaw",
]
YIDUN_TRIGGER_SELECTORS = [
    ".yidun_control",
    ".yidun",
]

# 题面目标字最长等待秒数，超时则刷新挑战
TARGET_WAIT_TIMEOUT = 8

YIDUN_REFRESH_SELECTORS = [
    ".yidun_refresh",
    ".yidun_top__refresh",
    "[class*='refresh']",
]


def find_yidun_widget(page, widget_selector=None):
    """定位页面上应操作的易盾 widget（优先已有图片挑战的实例）。"""
    if widget_selector:
        loc = page.locator(widget_selector)
        if loc.count():
            return loc.first

    candidates = []
    for sel in (".yidun--point", ".yidun--icon_point", ".yidun--icon", ".yidun--jigsaw", ".yidun"):
        loc = page.locator(sel)
        for i in range(loc.count()):
            item = loc.nth(i)
            try:
                if not item.is_visible():
                    continue
                score = 0
                if item.locator(".yidun_bgimg img[src^='http']").count():
                    score += 10
                if item.locator(".yidun_panel").first.is_visible():
                    score += 5
                if "yidun--success" in (item.get_attribute("class") or ""):
                    score += 20
                candidates.append((score, item))
            except Exception:
                continue
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    loc = page.locator(".yidun--point, .yidun--icon_point, .yidun--icon, .yidun--jigsaw, .yidun")
    if loc.count():
        return loc.first
    return None


def yidun_panel_visible(page, widget_selector=None):
    """判断易盾图片挑战面板是否已展开。"""
    root = find_yidun_widget(page, widget_selector)
    if not root:
        return False
    try:
        panel = root.locator(".yidun_panel").first
        if panel.count() and panel.is_visible():
            img = root.locator(".yidun_bgimg img, .yidun_bgimg").first
            return img.count() > 0 and img.is_visible()
    except Exception:
        pass
    return False


def trigger_yidun(page, pacer, widget_selector=None):
    """点击易盾验证条，弹出文字点选面板。"""
    if yidun_panel_visible(page, widget_selector):
        return True
    root = find_yidun_widget(page, widget_selector)
    if not root:
        return False
    try:
        root.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    pacer.pause(0.6, 1.2)
    for sel in YIDUN_TRIGGER_SELECTORS:
        btn = root.locator(sel).first
        if btn.count():
            try:
                box = btn.bounding_box()
                if box:
                    cx = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
                    cy = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
                    trace = get_mouse_state(page)
                    human_click_at(page, cx, cy, state=trace)
                    pacer.pause(1.0, 1.8)
                    return True
            except Exception:
                continue
    try:
        root.click(timeout=8000)
        pacer.pause(1.0, 1.8)
        return True
    except Exception:
        return False


def wait_yidun_image_ready(page, timeout_sec=12, pacer=None, widget_selector=None):
    """等待验证码图片 URL 加载完成。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        item, _ = locate_captcha_image(page, widget_selector)
        if item:
            try:
                src = item.get_attribute("src")
                if src and src.startswith("http"):
                    return True
                # 容器截图兜底：元素可见且有一定尺寸
                box = item.bounding_box()
                if box and box.get("width", 0) > 80 and box.get("height", 0) > 80:
                    return True
            except Exception:
                pass
        pacer.pause(0.35, 0.65)
    return False


def wait_yidun_challenge(page, timeout_sec=15, pacer=None, widget_selector=None):
    """等待文字点选面板与验证码图片加载完成。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if yidun_panel_visible(page, widget_selector):
            if wait_yidun_image_ready(page, timeout_sec=8, pacer=pacer, widget_selector=widget_selector):
                return True
        pacer.pause(0.4, 0.8)
    return yidun_panel_visible(page, widget_selector) and wait_yidun_image_ready(
        page, timeout_sec=3, pacer=pacer, widget_selector=widget_selector,
    )


def read_yidun_instruction(page, widget_selector=None):
    """从易盾面板读取「请依次点击 …」题面文字。"""
    root = find_yidun_widget(page, widget_selector)
    if root:
        try:
            txt = root.evaluate(
                """(el) => {
                    const sels = ['.yidun_tips__text', '.yidun_top__bar', '.yidun_tips'];
                    for (const sel of sels) {
                        const n = el.querySelector(sel);
                        if (n && n.textContent) return n.textContent.trim();
                    }
                    return '';
                }"""
            )
            if txt:
                return txt.strip()
        except Exception:
            pass
    scope = root if root else page
    best = ""
    for sel in YIDUN_TIP_SELECTORS:
        loc = scope.locator(sel)
        if not loc.count():
            continue
        for i in range(min(loc.count(), 3)):
            txt = (loc.nth(i).inner_text(timeout=2000) or "").strip()
            if not txt:
                continue
            if "依次" in txt or "点选" in txt or ("点击" in txt and re.search(r"[\u4e00-\u9fff]", txt)):
                return txt
            if len(txt) > len(best):
                best = txt
    return best


def _log_stealth_status(page):
    """打印当前页 webdriver 等指纹探测结果（调试用）。"""
    try:
        info = page.evaluate(
            """() => ({
                webdriver: navigator.webdriver,
                chrome: !!window.chrome,
                plugins: navigator.plugins ? navigator.plugins.length : 0,
                languages: navigator.languages,
            })"""
        )
        print(f"[stealth] 指纹探测: {info}", flush=True)
    except Exception:
        pass


def install_yidun_front_hook(page):
    """监听易盾 get 接口，缓存 front/bg 等字段（文字点选 + 滑块共用）。"""
    if getattr(page, "_yidun_front_hook", False):
        return
    page._yidun_front_cache = []
    page._yidun_bg_cache = []
    page._yidun_slice_cache = []
    page._yidun_front_hook = True

    def _on_response(resp):
        url = resp.url or ""
        if "necaptcha" not in url and "dun.163.com" not in url:
            return
        if "/get" not in url and "get?" not in url:
            return
        try:
            body = resp.text()
        except Exception:
            return
        if "front" not in body and "bg" not in body:
            return
        try:
            front_m = re.search(r'"front"\s*:\s*\[?\s*"([^"]+)"', body)
            if front_m:
                front = front_m.group(1).strip()
                if front:
                    page._yidun_front_cache.append(front)
                    if front.startswith("http"):
                        page._yidun_slice_cache.append(front)
                    print(f"[yidun] 网络 front={front!r}", flush=True)
            bg_m = re.search(r'"bg"\s*:\s*\[?\s*"([^"]+)"', body)
            if bg_m:
                bg = bg_m.group(1).strip()
                if bg:
                    page._yidun_bg_cache.append(bg)
                    print(f"[yidun] 网络 bg={bg[:80]!r}", flush=True)
        except Exception:
            pass

    page.on("response", _on_response)


def get_yidun_slide_urls_from_network(page):
    """从 get 响应缓存取最新滑块 bg / front(拼图块) URL。"""
    bg_cache = getattr(page, "_yidun_bg_cache", None) or []
    slice_cache = getattr(page, "_yidun_slice_cache", None) or []
    bg = bg_cache[-1] if bg_cache else ""
    sl = slice_cache[-1] if slice_cache else ""
    return bg, sl


def get_yidun_front_from_network(page):
    """从已监听的 get 响应缓存取最新文字点选目标字（跳过图片 URL）。"""
    cache = getattr(page, "_yidun_front_cache", None) or []
    for item in reversed(cache):
        if item and not str(item).startswith("http"):
            return item
    return ""


def parse_quoted_chars(text):
    """从「"安" "扩" "体"」或「安扩体」解析目标汉字。"""
    if not text:
        return ""
    quoted = re.findall(r'[「"\']([^「"\'\']+)[」"\']', text)
    if quoted:
        chars = []
        for q in quoted:
            for c in re.findall(r"[\u4e00-\u9fff]", q):
                if c not in INSTRUCTION_NOISE:
                    chars.append(c)
        if len(chars) >= 2:
            return "".join(chars)
    raw = re.sub(r"\s+", "", text)
    chars = [c for c in re.findall(r"[\u4e00-\u9fff]", raw) if c not in INSTRUCTION_NOISE]
    if len(chars) >= 2:
        return "".join(chars)
    return ""


def read_yidun_click_targets(page, widget_selector=None):
    """从易盾 DOM / 网络 front 读取需依次点击的目标汉字（如 来库扩）。"""
    front = get_yidun_front_from_network(page)
    if front and len(front) >= 2:
        return front.strip()

    root = find_yidun_widget(page, widget_selector)
    if not root:
        return ""

    try:
        targets = root.evaluate(
            """(el) => {
                const answer = el.querySelector('.yidun_tips__answer');
                if (answer) {
                    const point = answer.querySelector('.yidun_tips__point');
                    if (point && point.textContent) return point.textContent.trim();
                    if (answer.textContent) return answer.textContent.trim();
                }
                const tip = el.querySelector('.yidun_tips__text, .yidun_tips');
                if (!tip) return '';
                const picked = [];
                for (const n of tip.querySelectorAll('em, i, b, strong, span.yidun_tips__point')) {
                    const t = (n.textContent || '').trim();
                    if (t && t.length <= 2 && !/点击|依次|验证|刷新/.test(t)) {
                        picked.push(t);
                    }
                }
                if (picked.length >= 2) return picked.join('');
                const text = tip.textContent || '';
                const quoted = text.match(/[「"']([^「"'"]+)[」"']/g);
                if (quoted) {
                    return quoted.map(s => s.replace(/[「"'」"']/g, '')).join('');
                }
                return '';
            }"""
        )
        parsed = parse_quoted_chars(targets)
        if parsed and len(parsed) >= 2:
            return parsed
    except Exception:
        pass

    for sel in YIDUN_TARGET_SELECTORS:
        if not root:
            break
        loc = root.locator(sel)
        if not loc.count():
            continue
        txt = (loc.first.inner_text(timeout=1500) or "").strip()
        parsed = parse_quoted_chars(txt)
        if parsed and len(parsed) >= 2:
            return parsed

    return extract_click_targets(read_yidun_instruction(page, widget_selector))


def extract_click_targets(instruction):
    """从题面提取需依次点击的汉字/词组（供打码平台 extra 使用）。"""
    if not instruction:
        return ""
    quoted = re.findall(r'[「\"\']([^「\"\'\']+)[」\"\']', instruction)
    if quoted:
        return "".join(quoted)
    m = re.search(r"点击[「\"']?(.+?)[」\"']?$", instruction)
    if m:
        return re.sub(r"\s+", "", m.group(1))
    chars = [c for c in re.findall(r"[\u4e00-\u9fff]", instruction) if c not in INSTRUCTION_NOISE]
    if len(chars) >= 2:
        return "".join(chars)
    return ""


def wait_for_click_targets(page, widget_selector=None, timeout_sec=TARGET_WAIT_TIMEOUT, pacer=None):
    """限时等待题面目标字就绪，返回 (instruction, extra)。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    instruction = ""
    extra = ""
    while time.time() < deadline:
        instruction = read_yidun_instruction(page, widget_selector)
        extra = read_yidun_click_targets(page, widget_selector)
        if not extra:
            extra = get_yidun_front_from_network(page)
        if extra and len(extra) >= 2:
            return instruction, extra
        pacer.pause(0.35, 0.55)
    instruction = instruction or read_yidun_instruction(page, widget_selector)
    extra = extra or read_yidun_click_targets(page, widget_selector) or get_yidun_front_from_network(page)
    return instruction, extra


def reload_yidun_challenge(page, pacer, widget_selector=None):
    """刷新易盾挑战：优先点刷新按钮，否则重新触发验证条。"""
    root = find_yidun_widget(page, widget_selector)
    if root:
        for sel in YIDUN_REFRESH_SELECTORS:
            btn = root.locator(sel).first
            if btn.count():
                try:
                    if btn.is_visible():
                        btn.click(timeout=5000)
                        pacer.pause(1.2, 2.0)
                        wait_yidun_image_ready(page, timeout_sec=10, pacer=pacer, widget_selector=widget_selector)
                        print("[yidun] 已点击刷新按钮", flush=True)
                        return True
                except Exception:
                    continue
    print("[yidun] 未找到刷新按钮，重新触发验证条", flush=True)
    if trigger_yidun(page, pacer, widget_selector):
        wait_yidun_challenge(page, pacer=pacer, widget_selector=widget_selector, timeout_sec=12)
        return True
    return False


def locate_captcha_image(page, widget_selector=None):
    """定位验证码图片元素（img，用于下载原图）。"""
    root = find_yidun_widget(page, widget_selector)
    scope = root if root else page
    for sel in YIDUN_IMG_SELECTORS:
        loc = scope.locator(sel)
        if loc.count():
            item = loc.first
            try:
                if item.is_visible():
                    tag = (item.evaluate("el => el.tagName") or "").upper()
                    if tag == "IMG":
                        return item, sel
                    inner = item.locator("img").first
                    if inner.count() and inner.is_visible():
                        return inner, sel + " img"
            except Exception:
                continue
    return None, ""


def locate_click_area(page, widget_selector=None):
    """定位验证码可点击区域（优先 .yidun_bgimg 容器）。"""
    root = find_yidun_widget(page, widget_selector)
    scope = root if root else page
    for sel in YIDUN_CLICK_AREA_SELECTORS:
        loc = scope.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    box = loc.bounding_box()
                    if box and box.get("width", 0) > 60 and box.get("height", 0) > 60:
                        return loc, sel
            except Exception:
                continue
    return locate_captcha_image(page, widget_selector)


def capture_yidun_png(page, widget_selector=None):
    """截取易盾验证码图片，返回 (base64, selector)。"""
    import urllib.request

    item, sel = locate_captcha_image(page, widget_selector)
    if not item:
        raise RuntimeError("未找到易盾验证码图片元素")
    wait_yidun_image_ready(page, timeout_sec=12, widget_selector=widget_selector)

    # 优先从 img.src 下载原图（冰拓对 base64 质量更敏感）
    try:
        tag = (item.evaluate("el => el.tagName") or "").upper()
        if tag == "IMG":
            src = item.get_attribute("src") or ""
            if src.startswith("http"):
                req = urllib.request.Request(
                    src,
                    headers={"Referer": "https://dun.163.com/", "User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read()
                if len(raw) > 500:
                    print(f"[yidun] 图片下载 ok bytes={len(raw)} src={src[:80]}", flush=True)
                    return base64.b64encode(raw).decode("ascii"), sel
    except Exception as exc:
        print(f"[yidun] 图片 URL 下载失败，改用元素截图: {exc}", flush=True)

    png = item.screenshot(timeout=10000)
    if len(png) < 500:
        raise RuntimeError("验证码截图过小，可能面板未完全加载")
    print(f"[yidun] 元素截图 ok bytes={len(png)}", flush=True)
    return base64.b64encode(png).decode("ascii"), sel


def load_click_solver(platform):
    """加载打码平台适配器实例。"""
    import os
    from config_paths import load_project_config
    from adapters.base import discover, REGISTRY

    here = os.path.dirname(os.path.abspath(__file__))
    adapters_dir = os.path.join(here, "adapters")
    cfg, _ = load_project_config()
    discover(adapters_dir, external_paths=cfg.get("external_adapters") or [])
    cls = REGISTRY.get(platform)
    if not cls:
        raise RuntimeError(f"未找到平台适配器: {platform}")
    return cls(cfg.get(platform) or {})


def classify_yidun_click(platform, image_b64, extra_text, captcha_type=None):
    """调用打码平台识别文字点选坐标（冰拓可自动尝试备选类型）。"""
    solver = load_click_solver(platform)
    ctype = captcha_type or DEFAULT_CLICK_TYPE.get(platform)
    if ctype is None:
        raise RuntimeError(f"平台 {platform} 未配置默认 captcha_type，请传 --click-captcha-type")
    types_to_try = [ctype]
    if platform == "bingtop" and ctype not in BINGTOP_CLICK_FALLBACK:
        types_to_try.extend(BINGTOP_CLICK_FALLBACK)
    elif platform == "bingtop":
        types_to_try = [ctype] + [t for t in BINGTOP_CLICK_FALLBACK if t != ctype]
    last_exc = None
    for t in types_to_try:
        try:
            return solver.solve_click(
                image_b64, extra_text=extra_text, captcha_type=t,
            )
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "type error" in msg or "captcha type" in msg:
                continue
            if "请稍后再试" in str(exc) or "try again" in msg:
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("文字点选识别失败")


def parse_click_coords(raw):
    """
    解析打码平台返回的坐标字符串为 [[x,y], ...]。
    支持: x1,y1|x2,y2 / x1,y1,x2,y2 / JSON 数组。
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        pts = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                pts.append([float(item[0]), float(item[1])])
            elif isinstance(item, dict):
                x = item.get("x", item.get("X"))
                y = item.get("y", item.get("Y"))
                if x is not None and y is not None:
                    pts.append([float(x), float(y)])
        return pts
    if isinstance(raw, dict):
        data = raw.get("data") or raw.get("recognition") or raw.get("solution")
        if data is not None and data is not raw:
            return parse_click_coords(data)
        return []
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") or text.startswith("{"):
        try:
            return parse_click_coords(json.loads(text))
        except Exception:
            pass
    chunks = re.split(r"[|;]+", text)
    pts = []
    for chunk in chunks:
        nums = re.findall(r"-?\d+(?:\.\d+)?", chunk)
        if len(nums) >= 2:
            pts.append([float(nums[0]), float(nums[1])])
    if not pts and len(re.findall(r"-?\d+(?:\.\d+)?", text)) >= 2:
        nums = re.findall(r"-?\d+(?:\.\d+)?", text)
        for i in range(0, len(nums) - 1, 2):
            pts.append([float(nums[i]), float(nums[i + 1])])
    return pts


def click_yidun_points(page, img_selector, points, pacer, widget_selector=None, natural_wh=None, coord_image_wh=None):
    """拟人贝塞尔移动后点击验证码区域（易盾会采集 mousemove 轨迹）。"""
    root = find_yidun_widget(page, widget_selector)
    scope = root if root else page
    loc, area_sel = locate_click_area(page, widget_selector)
    if not loc:
        loc = scope.locator(img_selector).first
        area_sel = img_selector
    box = loc.bounding_box()
    if not box:
        raise RuntimeError(f"无法获取验证码点击区域: {area_sel}")

    # coord_image_wh：送给打码平台的图片尺寸（截图/上传图）；优先于 DOM naturalWidth
    nw, nh = coord_image_wh or natural_wh or (0, 0)
    if not nw or not nh:
        img_loc = scope.locator(".yidun_bgimg img").first
        if img_loc.count():
            natural = img_loc.evaluate(
                """(el) => ({
                    w: el.naturalWidth || el.clientWidth || el.width || 0,
                    h: el.naturalHeight || el.clientHeight || el.height || 0,
                })"""
            )
            nw = float(natural.get("w") or box["width"])
            nh = float(natural.get("h") or box["height"])
        else:
            nw = float(box["width"])
            nh = float(box["height"])

    sx = box["width"] / nw if nw > 0 else 1.0
    sy = box["height"] / nh if nh > 0 else 1.0
    print(
        f"[yidun] 点击区域={area_sel} box={box['width']:.0f}x{box['height']:.0f} "
        f"coord_img={nw:.0f}x{nh:.0f} scale={sx:.3f},{sy:.3f}",
        flush=True,
    )
    trace = get_mouse_state(page)
    pacer.pause(0.8, 1.6)
    for i, (px, py) in enumerate(points):
        rel_x = max(1.0, min(box["width"] - 1.0, px * sx + random.uniform(-2, 2)))
        rel_y = max(1.0, min(box["height"] - 1.0, py * sy + random.uniform(-2, 2)))
        abs_x = box["x"] + rel_x
        abs_y = box["y"] + rel_y
        human_click_at(page, abs_x, abs_y, state=trace)
        if i < len(points) - 1:
            pacer.pause(0.75, 1.45)
        else:
            pacer.pause(0.5, 1.0)


def is_yidun_success(page, widget_selector=None):
    """易盾文字点选是否已通过。"""
    root = find_yidun_widget(page, widget_selector)
    if not root:
        return False
    try:
        ok = root.evaluate(
            """(el) => {
                const cls = el.className || '';
                if (cls.includes('yidun--success')) return true;
                const ctrl = el.querySelector('.yidun_control');
                if (ctrl && (ctrl.className || '').includes('success')) return true;
                const tip = el.querySelector('.yidun_tips__text, .yidun_tips');
                const text = tip ? (tip.textContent || '') : '';
                if (/验证成功|通过验证|验证通过|success/i.test(text)) return true;
                const bar = el.querySelector('.yidun_control, .yidun_slide_indicator');
                if (bar && /成功|通过/.test(bar.textContent || '')) return true;
                return false;
            }"""
        )
        if ok:
            return True
    except Exception:
        pass
    return False


def solve_yidun_text_click(
    page,
    platform,
    captcha_type=None,
    widget_selector=None,
    auto_trigger=True,
    max_rounds=3,
    humanize_factor=1.3,
):
    """
    通用易盾文字点选流程：触发面板 → 读题面 → 平台识别 → 拟人点击。
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
                "points": [],
                "instruction": "",
                "last_error": "页面上未找到易盾验证码 widget",
            }
        if not wait_yidun_challenge(page, pacer=pacer, widget_selector=widget_selector):
            return {
                "ok": False,
                "rounds": 0,
                "points": [],
                "instruction": "",
                "last_error": "点击后未出现文字点选面板",
            }

    rounds = 0
    while rounds < max_rounds:
        if is_yidun_success(page, widget_selector):
            return {
                "ok": True,
                "rounds": rounds,
                "points": [],
                "instruction": read_yidun_instruction(page, widget_selector),
                "last_error": None,
            }

        if not yidun_panel_visible(page, widget_selector):
            if auto_trigger and rounds == 0:
                trigger_yidun(page, pacer, widget_selector)
                wait_yidun_challenge(page, pacer=pacer, widget_selector=widget_selector)
            if not yidun_panel_visible(page, widget_selector):
                last_error = "验证码面板不可见"
                break

        instruction, extra = wait_for_click_targets(
            page, widget_selector, timeout_sec=TARGET_WAIT_TIMEOUT, pacer=pacer,
        )
        front_net = get_yidun_front_from_network(page)
        api_extra = front_net if front_net and len(front_net) >= 2 else extra
        if front_net and extra and front_net != extra:
            print(f"[yidun] 使用网络 front={front_net!r}（DOM extra={extra!r}）", flush=True)
        if not api_extra or len(api_extra) < 2:
            last_error = f"题面目标字等待超时({TARGET_WAIT_TIMEOUT}s): {instruction!r}"
            print(f"[yidun] {last_error}，刷新挑战", flush=True)
            reload_yidun_challenge(page, pacer, widget_selector)
            rounds += 1
            continue

        try:
            img_b64, img_sel = capture_yidun_png(page, widget_selector)
            img_item, _ = locate_captcha_image(page, widget_selector)
            natural_wh = None
            if img_item:
                nat = img_item.evaluate(
                    """(el) => [el.naturalWidth||0, el.naturalHeight||0]"""
                )
                if nat and nat[0] > 0 and nat[1] > 0:
                    natural_wh = (float(nat[0]), float(nat[1]))
        except Exception as exc:
            last_error = f"截图失败: {exc}"
            pacer.pause(1.0, 1.5)
            rounds += 1
            continue

        points = []
        raw = None
        try:
            raw = classify_yidun_click(platform, img_b64, api_extra, captcha_type=captcha_type)
            points = parse_click_coords(raw)
        except Exception as exc:
            last_error = f"平台识别失败: {exc}"
            print(f"[yidun] 识别异常: {exc}", flush=True)
            pacer.pause(1.5, 2.5)
            rounds += 1
            continue

        if not points:
            last_error = f"平台未返回有效坐标: {raw!r}"
            print(
                f"[yidun] 第 {rounds + 1} 轮: 题面={instruction!r} extra={api_extra!r} 无坐标",
                flush=True,
            )
            pacer.pause(1.5, 2.5)
            rounds += 1
            continue

        if len(points) > len(api_extra):
            points = points[: len(api_extra)]

        print(
            f"[yidun] 第 {rounds + 1} 轮: 题面={instruction!r} extra={api_extra!r} "
            f"点击={points}",
            flush=True,
        )
        try:
            click_yidun_points(
                page, img_sel, points, pacer, widget_selector, natural_wh=natural_wh,
            )
        except Exception as exc:
            last_error = f"点击失败: {exc}"
            rounds += 1
            continue

        pacer.pause(2.5, 4.0)
        for _ in range(3):
            if is_yidun_success(page, widget_selector):
                rounds += 1
                return {
                    "ok": True,
                    "rounds": rounds,
                    "points": points,
                    "instruction": instruction,
                    "last_error": None,
                }
            pacer.pause(0.8, 1.2)
        rounds += 1
        last_error = "点击完成但未检测到验证成功，可能坐标偏差"

    return {
        "ok": is_yidun_success(page, widget_selector),
        "rounds": rounds,
        "points": [],
        "instruction": read_yidun_instruction(page, widget_selector),
        "last_error": last_error,
    }
