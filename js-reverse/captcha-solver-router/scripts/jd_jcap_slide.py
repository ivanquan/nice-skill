#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""京东 JCAP 滑动拼图验证码：浏览器抓图 + 打码识别 + 拟人拖拽（R2 混合）。"""

import base64
import time

from browser_stealth import get_mouse_state, human_slide_drag
from recaptcha_grid import HumanPacer
from yidun_slide import (
    calc_slide_drag_distance,
    classify_yidun_slide,
    parse_slide_offset,
)

DEFAULT_WIDGET = (
    "#captcha_modal, .captcha_modal_pc, .captcha_drop, "
    "#slideAuthCode, .slide-authCode-wraper, .JDValidate-wrap"
)
JD_OVERLAY_SELECTORS = [
    "#captcha_modal",
    ".captcha_modal_pc",
    ".captcha_modal_popup",
    ".captcha_drop",
    ".captcha_body",
    ".captcha_body .slot-content",
    ".captcha_footer",
    "#local_tip",
    "#slideAuthCode",
    ".slide-authCode-wraper",
    ".JDValidate-wrap",
    ".JDJRV-wrap",
    ".JDJRV-bigimg",
    ".JDJRV-bigimg img",
    ".JDJRV-bigimg canvas",
]
JD_BG_SELECTORS = [
    ".captcha_body .slot-content img",
    ".captcha_body img",
    ".JDJRV-bigimg img",
    "div.JDJRV-bigimg > img",
    ".jdcap-bigimg img",
]
JD_SLICE_SELECTORS = [
    ".JDJRV-smallimg img",
    "div.JDJRV-smallimg > img",
    ".jdcap-smallimg img",
]
JD_HANDLE_SELECTORS = [
    "#slider-div",
    ".captcha_footer .drag-box img",
    ".drag-box img",
    "#slide_path",
    ".JDJRV-slide-btn",
    ".JDJRV-slide-inner",
    "div.JDJRV-slide-btn",
    ".JDJRV-slide",
]
JD_SUCCESS_SELECTORS = [
    ".JDJRV-succ",
    ".JDJRV-success",
    ".jdcap-success",
]


def measure_jd_rotate_track_width(page):
    """读取新版京东旋转验证码滑轨宽度（px）。"""
    try:
        width = page.evaluate(
            """() => {
                const box = document.querySelector(
                    '.captcha_footer .drag-box, #local_footer .drag-box, .drag-box'
                );
                if (!box) return 0;
                const r = box.getBoundingClientRect();
                return r.width > 0 ? r.width : 0;
            }"""
        )
        if width and float(width) > 50:
            return float(width)
    except Exception:
        pass
    return 290.0


def find_jd_captcha_root(page, widget_selector=None):
    """定位京东 JCAP 验证码根节点。"""
    selectors = [s.strip() for s in (widget_selector or DEFAULT_WIDGET).split(",") if s.strip()]
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    return loc, sel
            except Exception:
                return loc, sel
    wrap = page.locator(".slide-authCode-wraper").first
    if wrap.count():
        try:
            if wrap.is_visible():
                return wrap, ".slide-authCode-wraper"
        except Exception:
            return wrap, ".slide-authCode-wraper"
    return None, None


def install_jd_jcap_hook(page):
    """在页面注入 JCAP check 响应缓存，便于抓取 bg/slice base64。"""
    page.evaluate(
        """() => {
            if (window.__jdJcapHookInstalled) return;
            window.__jdJcapHookInstalled = true;
            window.__jdJcapImages = { bg: null, slice: null, ts: 0 };
            const save = (obj) => {
                if (!obj || typeof obj !== 'object') return;
                const keys = Object.keys(obj);
                const pick = (klist) => {
                    for (const k of klist) {
                        const v = obj[k];
                        if (typeof v === 'string' && v.length > 200) return v;
                    }
                    return null;
                };
                const bg = pick(['b1', 'bg', 'bigImage', 'bigImg', 'background']);
                const sl = pick(['b2', 'slice', 'smallImage', 'smallImg', 'slideImage']);
                if (bg) window.__jdJcapImages.bg = bg;
                if (sl) window.__jdJcapImages.slice = sl;
                if (bg || sl) window.__jdJcapImages.ts = Date.now();
            };
            const origFetch = window.fetch;
            window.fetch = async (...args) => {
                const res = await origFetch(...args);
                try {
                    const url = (args[0] && args[0].url) ? args[0].url : String(args[0] || '');
                    if (/jcap|check|fp/i.test(url)) {
                        const clone = res.clone();
                        clone.json().then(save).catch(() => {});
                    }
                } catch (e) {}
                return res;
            };
            const XHR = window.XMLHttpRequest;
            function JDXHR() {
                const xhr = new XHR();
                const open = xhr.open;
                xhr.open = function (method, url) {
                    xhr.__jdUrl = url;
                    return open.apply(xhr, arguments);
                };
                xhr.addEventListener('load', function () {
                    try {
                        if (/jcap|check|fp/i.test(xhr.__jdUrl || '')) {
                            save(JSON.parse(xhr.responseText || '{}'));
                        }
                    } catch (e) {}
                });
                return xhr;
            }
            JDXHR.prototype = XHR.prototype;
            window.XMLHttpRequest = JDXHR;
        }"""
    )


def get_jd_jcap_images_from_hook(page):
    """从页面 hook 缓存读取 JCAP 背景图与滑块图 base64。"""
    try:
        data = page.evaluate("() => window.__jdJcapImages || {}")
        bg = data.get("bg")
        sl = data.get("slice")
        if bg and sl:
            return _normalize_b64(bg), _normalize_b64(sl)
    except Exception:
        pass
    return None, None


def _normalize_b64(raw):
    """剥离 data-uri 前缀，返回纯 base64。"""
    if not raw:
        return None
    text = str(raw).strip()
    if text.startswith("data:"):
        parts = text.split(",", 1)
        if len(parts) == 2:
            return parts[1]
    return text


def _b64_from_data_uri(src):
    """从 img src 的 data-uri 提取 base64。"""
    if not src or not str(src).startswith("data:image"):
        return None
    return _normalize_b64(src)


_OVERLAY_VISIBLE_JS = """
(selectors) => {
    const isVisibleEl = (el) => {
        if (!el) return false;
        const r = el.getBoundingClientRect();
        const st = window.getComputedStyle(el);
        return r.width > 20 && r.height > 20
            && st.visibility !== 'hidden'
            && st.display !== 'none'
            && parseFloat(st.opacity || '1') > 0.05;
    };
    const modal = document.querySelector('#captcha_modal, .captcha_modal_pc');
    if (modal && isVisibleEl(modal)) {
        const tip = (modal.innerText || '').replace(/\\s+/g, ' ').slice(0, 120);
        return { visible: true, selector: '#captcha_modal', reason: 'modal', hint: tip };
    }
    const drop = document.querySelector('.captcha_drop');
    if (drop && isVisibleEl(drop)) {
        const tip = (drop.innerText || '').replace(/\\s+/g, ' ').slice(0, 120);
        if (/安全验证|轨迹|绘制|滑块|拼图|旋转|使图片为正/.test(tip)) {
            return { visible: true, selector: '.captcha_drop', reason: 'drop+text', hint: tip };
        }
    }
    for (const s of selectors) {
        const el = document.querySelector(s);
        if (isVisibleEl(el)) return { visible: true, selector: s, reason: 'dom' };
    }
    const body = (document.body.innerText || '').replace(/\\s+/g, ' ');
    const captchaText = /安全验证|请按照|轨迹|绘制|滑块|拼图|旋转|使图片为正|刷新/.test(body);
    const wrap = document.querySelector('.slide-authCode-wraper, #slideAuthCode, .JDValidate-wrap');
    if (wrap && isVisibleEl(wrap) && captchaText) {
        return { visible: true, selector: 'wrap+text', reason: 'text', hint: body.slice(0, 120) };
    }
    return { visible: false, selector: null, reason: 'none', hint: body.slice(0, 120) };
}
"""


def jd_captcha_overlay_visible(page, widget_selector=None):
    """判断京东 JCAP 验证码挑战浮层是否正在展示（含轨迹/旋转/滑块）。"""
    selectors = list(JD_OVERLAY_SELECTORS)
    if widget_selector:
        for s in widget_selector.split(","):
            s = s.strip()
            if s and s not in selectors:
                selectors.insert(0, s)
    try:
        data = page.evaluate(_OVERLAY_VISIBLE_JS, selectors)
        if data.get("visible"):
            return True
    except Exception:
        pass
    return jd_captcha_panel_visible(page, widget_selector)


def jd_captcha_panel_visible(page, widget_selector=None):
    """判断京东 JCAP 滑块面板是否可见（兼容旧逻辑）。"""
    if jd_captcha_overlay_visible(page, widget_selector):
        for sel in JD_SLICE_SELECTORS:
            loc = page.locator(sel).first
            if loc.count():
                try:
                    if loc.is_visible():
                        return True
                except Exception:
                    return True
    root, _ = find_jd_captcha_root(page, widget_selector)
    if not root:
        return False
    try:
        for sel in JD_BG_SELECTORS + JD_SLICE_SELECTORS + JD_HANDLE_SELECTORS:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                return True
        txt = (root.inner_text(timeout=500) or "").strip()
        if txt and ("验证" in txt or "滑块" in txt):
            return True
    except Exception:
        pass
    return False


def is_jd_captcha_success(page, widget_selector=None, challenge_seen=False):
    """检测京东 JCAP 是否验证通过；仅见过挑战浮层后才把「浮层消失」视为成功。"""
    for sel in JD_SUCCESS_SELECTORS:
        loc = page.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    return True
            except Exception:
                return True
    err = page.locator(".JDJRV-error, .jdcap-error").first
    if err.count():
        try:
            if err.is_visible():
                return False
        except Exception:
            pass
    if challenge_seen and not jd_captcha_overlay_visible(page, widget_selector):
        return True
    return False


def trigger_jd_pwd_login(page, username, password, pacer=None):
    """在密码登录表单填入账号密码并点击登录，触发 JCAP。"""
    if pacer is None:
        pacer = HumanPacer()
    if not username or not password:
        return False
    try:
        # 确保处于密码登录（部分页面默认扫码）
        for tab_sel in (
            ".login-tab-r",
            "#pwd-login",
            "a[data-login-type='pwd']",
            "text=密码登录",
        ):
            tab = page.locator(tab_sel).first
            if tab.count():
                try:
                    if tab.is_visible():
                        tab.click(timeout=3000)
                        pacer.pause(0.4, 0.8)
                        break
                except Exception:
                    pass

        user_loc = None
        for sel in ("#loginname", "input#loginname", "input[name='loginname']"):
            loc = page.locator(sel).first
            if loc.count():
                user_loc = loc
                break
        if not user_loc:
            user_loc = page.get_by_placeholder("账号名/手机号/邮箱").first
        user_loc.wait_for(state="visible", timeout=15000)
        user_loc.fill(str(username), timeout=10000)
        pacer.pause(0.3, 0.6)

        pwd_loc = None
        for sel in ("#nloginpwd", "input#nloginpwd", "input[name='nloginpwd']", "input[type='password']"):
            loc = page.locator(sel).first
            if loc.count():
                pwd_loc = loc
                break
        if not pwd_loc:
            pwd_loc = page.get_by_placeholder("密码").first
        pwd_loc.fill(str(password), timeout=10000)
        pacer.pause(0.4, 0.8)

        clicked = False
        for sel in ("#loginsubmit", "a#loginsubmit", ".login-btn", "a.btn-entry", "text=登录"):
            btn = page.locator(sel).first
            if btn.count():
                try:
                    btn.click(timeout=10000)
                    clicked = True
                    break
                except Exception:
                    continue
        if clicked:
            print("[jd-login] 已点击登录，等待验证码浮层…", flush=True)
            pacer.pause(2.0, 3.5)
            return True
    except Exception as exc:
        print(f"[jd-jcap-slide] 触发密码登录失败: {exc}", flush=True)
    return False


def wait_jd_slide_ready(page, timeout_sec=20, pacer=None, widget_selector=None):
    """等待京东 JCAP 滑块面板与图片加载完成。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if jd_captcha_panel_visible(page, widget_selector):
            bg, sl = get_jd_jcap_images_from_hook(page)
            if bg and sl:
                return True
            for bsel in JD_BG_SELECTORS:
                bl = page.locator(bsel).first
                if bl.count() and bl.is_visible():
                    src = bl.get_attribute("src") or ""
                    if _b64_from_data_uri(src):
                        for ssel in JD_SLICE_SELECTORS:
                            sloc = page.locator(ssel).first
                            if sloc.count() and sloc.is_visible():
                                ssrc = sloc.get_attribute("src") or ""
                                if _b64_from_data_uri(ssrc):
                                    return True
        pacer.pause(0.45, 0.75)
    return jd_captcha_panel_visible(page, widget_selector)


def capture_jd_slide_images(page, widget_selector=None):
    """获取京东 JCAP 背景图与滑块图 base64。"""
    bg, sl = get_jd_jcap_images_from_hook(page)
    if bg and sl:
        print("[jd-jcap-slide] hook 缓存获取 bg+slice", flush=True)
        return bg, sl

    bg_b64 = None
    slice_b64 = None
    for sel in JD_BG_SELECTORS:
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            src = loc.get_attribute("src") or ""
            bg_b64 = _b64_from_data_uri(src)
            if not bg_b64:
                png = loc.screenshot(timeout=10000)
                bg_b64 = base64.b64encode(png).decode("ascii")
            if bg_b64:
                break
    for sel in JD_SLICE_SELECTORS:
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            src = loc.get_attribute("src") or ""
            slice_b64 = _b64_from_data_uri(src)
            if not slice_b64:
                png = loc.screenshot(timeout=10000)
                slice_b64 = base64.b64encode(png).decode("ascii")
            if slice_b64:
                break
    if not bg_b64 or not slice_b64:
        raise RuntimeError("未找到 JCAP 背景图或滑块图")
    print("[jd-jcap-slide] DOM 获取 bg+slice ok", flush=True)
    return bg_b64, slice_b64


def measure_jd_slide_geometry(page, widget_selector=None):
    """读取京东 JCAP 滑块几何参数，用于距离换算。"""
    try:
        geom = page.evaluate(
            """() => {
                const bg = document.querySelector('.JDJRV-bigimg img, div.JDJRV-bigimg > img');
                const slice = document.querySelector('.JDJRV-smallimg img, div.JDJRV-smallimg > img');
                const track = document.querySelector('.JDJRV-slide-bg, .JDJRV-wrap, .JDJRV-slide');
                const handle = document.querySelector('.JDJRV-slide-btn, .JDJRV-slide-inner');
                const br = bg ? bg.getBoundingClientRect() : {};
                const sr = slice ? slice.getBoundingClientRect() : {};
                const tr = track ? track.getBoundingClientRect() : {};
                const hr = handle ? handle.getBoundingClientRect() : {};
                return {
                    bgNaturalW: bg ? (bg.naturalWidth || br.width || 275) : 275,
                    bgDisplayW: br.width || 275,
                    sliceNaturalW: slice ? (slice.naturalWidth || sr.width || 55) : 55,
                    sliceDisplayW: sr.width || 55,
                    trackW: tr.width || br.width || 275,
                    handleW: hr.width || 40,
                };
            }"""
        )
        return geom
    except Exception:
        return None


def locate_jd_slider_handle(page, widget_selector=None):
    """定位京东 JCAP 滑块拖拽手柄。"""
    for sel in JD_HANDLE_SELECTORS:
        loc = page.locator(sel).first
        if loc.count():
            try:
                if loc.is_visible():
                    return loc, sel
            except Exception:
                return loc, sel
    raise RuntimeError("未找到京东 JCAP 滑块手柄")


def scale_jd_slide_offset(page, offset_logic, widget_selector=None):
    """将打码平台缺口坐标换算为轨道拖拽像素。"""
    geom = measure_jd_slide_geometry(page, widget_selector)
    return calc_slide_drag_distance(offset_logic, geom)


def drag_jd_slider(page, offset_px, widget_selector=None, pacer=None):
    """拟人拖拽京东 JCAP 滑块手柄。"""
    if pacer is None:
        pacer = HumanPacer()
    handle, sel = locate_jd_slider_handle(page, widget_selector)
    box = handle.bounding_box()
    if not box:
        raise RuntimeError(f"无法获取滑块手柄位置: {sel}")
    sx = box["x"] + box["width"] / 2
    sy = box["y"] + box["height"] / 2
    tx = sx + float(offset_px)
    print(f"[jd-jcap-slide] 拖拽 {sel} offset={offset_px:.1f}px", flush=True)
    pacer.pause(0.5, 1.0)
    human_slide_drag(page, sx, sy, tx, sy, state=get_mouse_state(page), accurate=True)


def solve_jd_jcap_slide(
    page,
    platform,
    captcha_type=None,
    widget_selector=None,
    auto_trigger=True,
    max_rounds=3,
    humanize_factor=1.3,
    login_user=None,
    login_pass=None,
):
    """
    京东 JCAP 滑动拼图 R2 混合流程：触发登录 → 抓图识别 → 拟人拖拽 → 页面 JS 加密提交。
    """
    pacer = HumanPacer(humanize_factor)
    install_jd_jcap_hook(page)
    last_error = None

    if auto_trigger and login_user and login_pass:
        trigger_jd_pwd_login(page, login_user, login_pass, pacer)
        if not wait_jd_slide_ready(page, pacer=pacer, widget_selector=widget_selector):
            return {
                "ok": False,
                "rounds": 0,
                "offset": 0,
                "last_error": "点击登录后未出现 JCAP 滑块面板（可能未触发风控或账号错误）",
            }
    elif auto_trigger and not jd_captcha_panel_visible(page, widget_selector):
        return {
            "ok": False,
            "rounds": 0,
            "offset": 0,
            "last_error": "验证码未弹出；请传 login_user/login_pass 或手动触发后设 --no-auto-trigger",
        }

    rounds = 0
    while rounds < max_rounds:
        if is_jd_captcha_success(page, widget_selector, challenge_seen=True):
            return {"ok": True, "rounds": rounds, "offset": 0, "last_error": None}

        if not jd_captcha_panel_visible(page, widget_selector):
            last_error = "JCAP 滑块面板不可见"
            break

        pacer.pause(0.5, 1.0)
        try:
            bg_b64, slice_b64 = capture_jd_slide_images(page, widget_selector)
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
            print(f"[jd-jcap-slide] 识别异常: {exc}", flush=True)
            rounds += 1
            pacer.pause(1.5, 2.5)
            continue

        if offset_logic <= 0:
            last_error = f"平台未返回有效距离: {raw!r}"
            rounds += 1
            continue

        offset_px = scale_jd_slide_offset(page, offset_logic, widget_selector)
        print(
            f"[jd-jcap-slide] 第 {rounds + 1} 轮: logic={offset_logic} drag={offset_px:.1f}",
            flush=True,
        )

        try:
            drag_jd_slider(page, offset_px, widget_selector, pacer)
        except Exception as exc:
            last_error = f"拖拽失败: {exc}"
            rounds += 1
            continue

        pacer.pause(2.0, 3.5)
        for _ in range(5):
            if is_jd_captcha_success(page, widget_selector, challenge_seen=True):
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
        "ok": is_jd_captcha_success(page, widget_selector, challenge_seen=True),
        "rounds": rounds,
        "offset": 0,
        "last_error": last_error,
    }
