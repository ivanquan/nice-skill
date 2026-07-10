#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R2 自动化点击过 / 协议驱动过 —— 多后端反爬浏览器引擎（全 Python）。

把「平台/协议给出的 坐标 / 距离 / 角度 / 令牌」用拟人浏览器操作过掉验证码。

支持后端 (--backend):
  cloak        : CloakBrowser  —— 源码级隐形 Chromium，drop-in Playwright，强反爬首选
  drissionpage : DrissionPage  —— 轻量，自带反检测，中文友好，单页滑块/点选省事
  playwright   : 原生 Playwright —— 需自行加 stealth（见 references/automation.md §5）

支持操作 (--op):
  slide  : 滑块 —— 给定像素偏移 offset，拟人拖拽
  click  : 点选 —— 给定相对验证码图片的像素坐标列表，依次点击
  rotate : 旋转 —— 给定角度 angle，换算水平位移拖拽旋转手柄
  rotate-captcha : 旋转 R2 —— 截图 + 平台识别角度 + 拟人拖拽手柄（通用）
  track  : 轨迹绘制 —— 截图 + 平台识别路径点 + 拟人沿轨迹绘制
  token  : token 类 —— 先调 solve.py 解出令牌，再注入页面（R1 接 R2）
  recaptcha-grid : reCAPTCHA v2 图片九宫格 —— 配合 --wait-manual 手动触发后平台识别+点击
  yidun-click    : 网易易盾文字点选 —— 自动触发面板 + 平台识别坐标 + 拟人点击
  yidun-slide    : 网易易盾滑动拼图 —— 自动触发面板 + 平台识别距离 + 拟人拖拽（见 references/yidun-r2-automation.md）
  jd-jcap-slide  : 京东 JCAP 滑动拼图 —— 密码登录触发 + 浏览器抓图 + 平台识别 + 拟人拖拽（加密提交走页面 JS）
  jd-login-captcha : 京东登录 Demo —— 自动识别轨迹/旋转/滑块并调用对应通用 R2 解法
  icon-click     : 通用图标点选 —— Provider 可插拔（内置 yidun），背景图+提示图识别 + 拟人点击

示例:
  python automate.py --backend cloak --op slide --target-url URL --slider-selector "#slider" --offset 128
  python automate.py --backend playwright --op icon-click --target-url "https://dun.163.com/trial/icon-click" --platform bingtop --click-provider yidun
  python automate.py --backend drissionpage --op click --target-url URL --captcha-img-selector "#cap" --points "[[120,80],[200,150]]"
  python automate.py --backend playwright --op slide --target-url URL --slider-selector ".slider" --offset 128 --chrome-path "%CHROME_EXECUTABLE%"
  python automate.py --backend playwright --op yidun-slide --target-url "https://dun.163.com/trial/jigsaw" --platform bingtop --yidun-widget-selector ".yidun--jigsaw, .yidun"
  python automate.py --backend cloak --op token --target-url URL --platform yescaptcha --sitekey 6Le-xxx --url URL

注意:
  - Chrome 可执行文件路径请在**项目目录** config.json 的 automation.chrome_executable 配置，或 --chrome-path / 环境变量 CHROME_EXECUTABLE。
  - 后端包缺失时给出明确安装提示，不崩溃。
  - 拟人轨迹为贝塞尔缓动 + 随机抖动，但仍需按目标站点节奏微调。
  - token 注入对现代 reCAPTCHA v3 / 企业版（iframe + 业务 POST）不一定生效，
    更推荐 R1 直接在业务请求里带 gRecaptchaResponse（见 SKILL.md 第 5 步）。
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def load_automation_config():
    """从项目 config.json 读取 automation 段（Chrome 路径等）。"""
    from config_paths import load_project_config
    cfg, _ = load_project_config()
    return cfg.get("automation") or {}


def resolve_chrome_executable(cli_path=None):
    """
    解析 Playwright 使用的 Chrome 路径：CLI > config.json > 环境变量 > None（用 Playwright 自带 Chromium）。
    """
    if cli_path and str(cli_path).strip():
        exe = str(cli_path).strip()
        if not os.path.isfile(exe):
            raise SystemExit(f"Chrome 可执行文件不存在: {exe}")
        return exe
    auto = load_automation_config()
    for candidate in (
        (auto.get("chrome_executable") or "").strip(),
        os.environ.get("CHROME_EXECUTABLE", "").strip(),
        os.environ.get("GOOGLE_CHROME_SHIM", "").strip(),
    ):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


# ----------------------------------------------------------------------------
# 拟人运动工具
# ----------------------------------------------------------------------------
def bezier_path(x0, y0, x1, y1, n=30):
    """生成贝塞尔缓动轨迹点，控制点带随机偏移，单步带 ±1px 抖动。"""
    ctrl_x = (x0 + x1) / 2 + random.uniform(-20, 20)
    ctrl_y = (y0 + y1) / 2 + random.uniform(-15, 15)
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt * mt * x0 + 2 * mt * t * ctrl_x + t * t * x1
        y = mt * mt * y0 + 2 * mt * t * ctrl_y + t * t * y1
        x += random.uniform(-1, 1)
        y += random.uniform(-1, 1)
        pts.append((round(x, 1), round(y, 1)))
    return pts


def human_sleep(a=0.05, b=0.18):
    time.sleep(random.uniform(a, b))


def _to_pw_proxy(proxy):
    if not proxy:
        return None
    # 接受 "http://user:pass@host:port" 或 "socks5://..."
    return {"server": proxy}


# ----------------------------------------------------------------------------
# 后端启动
# ----------------------------------------------------------------------------
def launch_backend(backend, headless=True, proxy=None, humanize=True, chrome_path=None):
    if backend == "cloak":
        try:
            from cloakbrowser import launch
        except ImportError:
            raise SystemExit("未安装 cloakbrowser，请运行: pip install cloakbrowser")
        return launch(headless=headless, humanize=humanize, proxy=proxy)

    if backend == "playwright":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SystemExit("未安装 playwright，请运行: pip install playwright")
        pw = sync_playwright().start()
        from browser_stealth import (
            CHROME_STEALTH_LAUNCH_ARGS,
            PLAYWRIGHT_IGNORE_DEFAULT_ARGS,
            build_playwright_launch_kwargs,
            warn_if_builtin_chromium,
        )

        exe = resolve_chrome_executable(chrome_path)
        warn_if_builtin_chromium(exe)
        launch_kw = build_playwright_launch_kwargs(
            headless=headless, proxy=_to_pw_proxy(proxy), chrome_path=exe,
        )
        browser = pw.chromium.launch(**launch_kw)
        browser._playwright = pw  # 便于 finally 里 stop
        return browser

    if backend == "drissionpage":
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
        except ImportError:
            raise SystemExit("未安装 DrissionPage，请运行: pip install DrissionPage")
        from browser_stealth import CHROME_STEALTH_LAUNCH_ARGS

        co = ChromiumOptions().headless(headless)
        for arg in CHROME_STEALTH_LAUNCH_ARGS:
            co.set_argument(arg)
        if proxy:
            co.set_proxy(proxy)
        return ChromiumPage(co)

    raise SystemExit(f"未知后端: {backend}（支持 cloak / drissionpage / playwright）")


def new_page(backend, browser, target_url, wait_until="domcontentloaded", stealth=True):
    """返回 (page, is_dp)。DrissionPage 的 page 即 ChromiumPage 本身。"""
    if backend == "drissionpage":
        browser.get(target_url)
        return browser, True

    from browser_stealth import apply_page_stealth, apply_playwright_cdp_stealth, create_stealth_context

    ctx = None
    if stealth:
        ctx = create_stealth_context(browser, backend=backend)
        page = ctx.new_page()
    else:
        page = browser.new_page()
        apply_page_stealth(page, backend=backend)
    page._pw_context = ctx
    page._stealth_backend = backend
    if stealth and backend == "playwright":
        apply_playwright_cdp_stealth(page, backend=backend)
    page.goto(target_url, wait_until=wait_until, timeout=60000)
    return page, False


# ----------------------------------------------------------------------------
# Playwright / CloakBrowser 版操作（共用 stealth 拟人鼠标）
# ----------------------------------------------------------------------------
def _pw_slide(page, slider_sel, offset):
    from browser_stealth import get_mouse_state, human_slide_drag

    box = page.locator(slider_sel).bounding_box()
    if not box:
        raise RuntimeError(f"找不到滑块元素: {slider_sel}")
    sx = box["x"] + box["width"] / 2
    sy = box["y"] + box["height"] / 2
    human_slide_drag(page, sx, sy, sx + float(offset), sy, state=get_mouse_state(page))


def _pw_click(page, img_sel, points):
    from browser_stealth import get_mouse_state, human_click_at

    box = page.locator(img_sel).bounding_box()
    if not box:
        raise RuntimeError(f"找不到验证码图片元素: {img_sel}")
    state = get_mouse_state(page)
    for px, py in points:
        human_click_at(page, box["x"] + px, box["y"] + py, state=state)
        human_sleep(0.2, 0.5)


def _pw_rotate(page, handle_sel, angle, track_width=300, full_angle=360):
    from browser_stealth import get_mouse_state, human_drag

    px = int(track_width * angle / full_angle)
    box = page.locator(handle_sel).bounding_box()
    if not box:
        raise RuntimeError(f"找不到旋转手柄: {handle_sel}")
    sx = box["x"] + box["width"] / 2
    sy = box["y"] + box["height"] / 2
    human_drag(page, sx, sy, sx + px, sy, state=get_mouse_state(page))


_TOKEN_INJECT_JS = """(tok) => {
    const sels = [
        'textarea[id^="g-recaptcha-response"]',
        'textarea[name="g-recaptcha-response"]',
        'textarea[id^="h-captcha-response"]',
        'textarea[name="h-captcha-response"]',
        'textarea[id^="cf-turnstile-response"]',
        'textarea[name="cf-turnstile-response"]'
    ];
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    let hit = 0;
    for (const s of sels) {
        for (const n of document.querySelectorAll(s)) {
            setter.call(n, tok);
            n.dispatchEvent(new Event('input', {bubbles: true}));
            n.dispatchEvent(new Event('change', {bubbles: true}));
            hit++;
        }
    }
    const w = document.querySelector('.g-recaptcha, .h-captcha');
    if (w && w.dataset && w.dataset.callback) {
        try { window[w.dataset.callback](tok); } catch (e) {}
    }
    if (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) {
        const invokeCb = (obj, depth) => {
            if (!obj || depth > 10) return;
            if (typeof obj === 'object') {
                if (typeof obj.callback === 'function') {
                    try { obj.callback(tok); } catch (e) {}
                }
                for (const k of Object.keys(obj)) invokeCb(obj[k], depth + 1);
            }
        };
        for (const cid of Object.keys(window.___grecaptcha_cfg.clients)) {
            invokeCb(window.___grecaptcha_cfg.clients[cid], 0);
        }
    }
    return hit;
}"""


def _pw_token(page, token):
    """向主文档及所有 iframe 注入 token，并在主文档触发 reCAPTCHA 回调。"""
    total = 0
    for frame in page.frames:
        try:
            total += frame.evaluate(_TOKEN_INJECT_JS, token) or 0
        except Exception:
            pass
    return total


# ----------------------------------------------------------------------------
# DrissionPage 版操作
# ----------------------------------------------------------------------------
def _dp_slide(page, slider_sel, offset):
    slider = page.ele(slider_sel)
    slider.drag(offset, 0, duration=1.2)


def _dp_click(page, img_sel, points):
    cap = page.ele(img_sel)
    for px, py in points:
        cap.click.at((px, py))
        human_sleep(0.2, 0.5)


def _dp_rotate(page, handle_sel, angle, track_width=300, full_angle=360):
    px = int(track_width * angle / full_angle)
    handle = page.ele(handle_sel)
    handle.drag(px, 0, duration=1.0)


# ----------------------------------------------------------------------------
# token 类：先调 solve.py 解出令牌
# ----------------------------------------------------------------------------
def solve_token_via_cli(platform, sitekey, url, extra=None):
    cmd = [
        sys.executable, os.path.join(HERE, "solve.py"),
        "--platform", platform, "--op", "token",
        "--sitekey", sitekey, "--url", url,
    ]
    if extra:
        cmd += extra
    out = subprocess.check_output(cmd, text=True)
    # solve.py 末尾打印一行 JSON: {"token": "...", ...}
    for line in reversed(out.strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("solve.py 未返回可解析的 JSON")


# ----------------------------------------------------------------------------
# 调度
# ----------------------------------------------------------------------------
def _close_page(page, is_dp=False):
    """关闭 Page 及其 stealth BrowserContext。"""
    if is_dp or page is None:
        return
    from browser_stealth import close_page_context

    close_page_context(page)
    try:
        page.close()
    except Exception:
        pass


def _close_browser(browser):
    """关闭浏览器并释放 Playwright 实例。"""
    pw = getattr(browser, "_playwright", None)
    try:
        browser.close()
    except Exception:
        pass
    if pw:
        try:
            pw.stop()
        except Exception:
            pass


# Submit / 验证成功判定
# ----------------------------------------------------------------------------
SUCCESS_TEXT_KEYWORDS = (
    "verification success",
    "successfully verified",
    "验证成功",
    "已成功",
    "success",
)


def _verify_submit_success(page, success_selector=None, timeout_ms=25000):
    """
    综合判定 reCAPTCHA / 表单提交是否成功。
    返回 (verified: bool, verify_tip: str, signals: dict)。
    """
    deadline = time.time() + timeout_ms / 1000.0
    last_signals = {}
    while time.time() < deadline:
        try:
            last_signals = page.evaluate(
                """(kw) => {
                    const signals = {};
                    if (window.grecaptcha && typeof window.grecaptcha.getResponse === 'function') {
                        const r = window.grecaptcha.getResponse() || '';
                        signals.grecaptcha_len = r.length;
                        signals.grecaptcha_ok = r.length > 20;
                    }
                    for (const ta of document.querySelectorAll('textarea[name="g-recaptcha-response"]')) {
                        const v = ta.value || '';
                        if (v.length > 20) {
                            signals.textarea_len = v.length;
                            signals.textarea_ok = true;
                        }
                    }
                    const anchor = document.querySelector('#recaptcha-anchor');
                    if (anchor) {
                        signals.anchor_checked = anchor.getAttribute('aria-checked') === 'true'
                            || (anchor.className || '').includes('recaptcha-checkbox-checked');
                    }
                    return signals;
                }""",
                list(SUCCESS_TEXT_KEYWORDS),
            )
        except Exception:
            last_signals = {}

        result_text = ""
        if success_selector:
            try:
                el = page.locator(success_selector).first
                if el.count():
                    result_text = (el.inner_text(timeout=500) or "").strip()
                    if not result_text:
                        result_text = (el.text_content(timeout=500) or "").strip()
            except Exception:
                result_text = ""

        if result_text:
            lower = result_text.lower()
            matched = [k for k in SUCCESS_TEXT_KEYWORDS if k in lower or k in result_text]
            if matched:
                return True, result_text[:300], {
                    **last_signals,
                    "result_text": result_text[:120],
                    "keyword_hits": matched,
                }
            # Demo 页有文案但未命中关键词 — 仍视为已出现结果
            if len(result_text) > 10 and "error" not in lower and "失败" not in result_text:
                return True, result_text[:300], {**last_signals, "result_text": result_text[:120]}

        if last_signals.get("grecaptcha_ok") or last_signals.get("textarea_ok"):
            if last_signals.get("anchor_checked"):
                tip = result_text or "grecaptcha token + checkbox checked"
                return True, tip[:300], last_signals

        time.sleep(0.4)

    tip = ""
    if success_selector:
        try:
            tip = (page.locator(success_selector).first.inner_text(timeout=500) or "").strip()
        except Exception:
            pass
    return False, tip[:300] if tip else "", last_signals


def _pw_post_click(page, selector):
    """点击 Submit；若被验证码浮层遮挡则 force 或 JS 触发。"""
    try:
        loc = page.locator(selector).first
        try:
            loc.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass
        try:
            loc.click(timeout=8000)
            return "click"
        except Exception:
            pass
        try:
            loc.click(force=True, timeout=5000)
            return "force_click"
        except Exception:
            pass
        page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (el) el.click();
            }""",
            selector,
        )
        return "js_click"
    except Exception as exc:
        return f"failed:{type(exc).__name__}"


def _wait_gt3_success(page, timeout_ms=8000):
    """等待 GT3 验证成功 DOM 标志。"""
    selectors = [
        ".geetest_success_radar_tip",
        ".geetest_success",
        ".geetest_radar_success",
    ]
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        for sel in selectors:
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                try:
                    txt = loc.first.inner_text(timeout=500)
                except Exception:
                    txt = sel
                return True, (txt.strip() if txt else sel)
        btn = page.locator(".geetest_radar_btn")
        if btn.count():
            cls = btn.first.get_attribute("class") or ""
            if "success" in cls:
                return True, "geetest_radar_btn.success"
        time.sleep(0.25)
    return False, None


def run(backend, op, target_url, headless, proxy, humanize, wait_selector=None, pre_click=None,
        hold_seconds=3, chrome_path=None, wait_until="domcontentloaded", success_selector=None,
        verify_gt3=False, post_click=None, wait_manual=False, wait_signal=None,
        grid_max_rounds=8, grid_confidence=0.5, auto_anchor=True, humanize_factor=1.3,
        click_captcha_type=None, yidun_widget_selector=None, widget_selector=None,
        click_provider="auto", click_max_rounds=3,
        no_auto_trigger=False, stealth=True, **kw):
    widget_sel = widget_selector or yidun_widget_selector
    browser = launch_backend(backend, headless=headless, proxy=proxy, humanize=humanize, chrome_path=chrome_path)
    page = None
    is_dp = False
    try:
        page, is_dp = new_page(backend, browser, target_url, wait_until=wait_until, stealth=stealth)

        if op in ("yidun-click", "yidun-slide", "icon-click", "jd-jcap-slide", "jd-login-captcha") and not is_dp:
            if op in ("jd-jcap-slide", "jd-login-captcha"):
                from jd_jcap_slide import install_jd_jcap_hook
                install_jd_jcap_hook(page)
            else:
                from yidun_click import install_yidun_front_hook
                install_yidun_front_hook(page)

        if pre_click and not is_dp:
            page.wait_for_selector(pre_click, state="visible", timeout=30000)
            page.locator(pre_click).first.click()
            human_sleep(1.0, 2.0)
            if op in ("yidun-click", "icon-click") and widget_sel:
                try:
                    page.wait_for_selector(widget_sel, state="visible", timeout=15000)
                    human_sleep(0.8, 1.5)
                except Exception:
                    pass
            if op in ("yidun-slide", "track", "rotate-captcha") and widget_sel:
                try:
                    page.wait_for_selector(widget_sel, state="visible", timeout=15000)
                    human_sleep(0.8, 1.5)
                except Exception:
                    pass
            if op in ("track", "rotate-captcha") and kw.get("captcha_img_selector"):
                try:
                    page.wait_for_selector(kw["captcha_img_selector"], state="visible", timeout=15000)
                    human_sleep(0.8, 1.5)
                except Exception:
                    pass

        if wait_selector and not is_dp:
            page.wait_for_selector(wait_selector, state="visible", timeout=30000)
            human_sleep(0.5, 1.0)

        if op == "slide":
            offset = float(kw["offset"])
            if is_dp:
                _dp_slide(page, kw["slider_selector"], offset)
            else:
                _pw_slide(page, kw["slider_selector"], offset)

        elif op == "click":
            points = json.loads(kw["points"])
            if is_dp:
                _dp_click(page, kw["captcha_img_selector"], points)
            else:
                _pw_click(page, kw["captcha_img_selector"], points)

        elif op == "rotate":
            angle = float(kw["angle"])
            tw = float(kw.get("track_width", 300))
            if is_dp:
                _dp_rotate(page, kw["handle_selector"], angle, tw)
            else:
                _pw_rotate(page, kw["handle_selector"], angle, tw)

        elif op == "recaptcha-grid":
            from recaptcha_grid import (
                solve_recaptcha_v2,
                grecaptcha_response,
                anchor_checked,
                wait_challenge_closed,
                challenge_visible,
                is_recaptcha_solved,
            )
            platform = kw["platform"]
            captcha_res = solve_recaptcha_v2(
                page,
                platform,
                auto_click_anchor=auto_anchor and not (wait_manual or wait_signal),
                wait_manual=wait_manual,
                wait_signal=wait_signal,
                max_rounds=int(grid_max_rounds),
                confidence=float(grid_confidence),
                humanize_factor=float(humanize_factor),
            )
            verified = None
            verify_tip = None
            verify_signals = None
            post_click_mode = None
            captcha_ok = bool(captcha_res.get("ok")) or is_recaptcha_solved(page)
            if post_click and not is_dp and captcha_ok:
                wait_challenge_closed(page, timeout_sec=40)
                human_sleep(0.8, 1.5)
                if challenge_visible(page) and not anchor_checked(page):
                    captcha_res["last_error"] = (
                        (captcha_res.get("last_error") or "")
                        + "；挑战浮层仍在，后续提交可能失败"
                    ).strip("；")
                else:
                    post_click_mode = _pw_post_click(page, post_click)
                    human_sleep(1.0, 2.0)
            if success_selector:
                verified, verify_tip, verify_signals = _verify_submit_success(
                    page, success_selector=success_selector, timeout_ms=25000,
                )
            elif captcha_ok and is_recaptcha_solved(page):
                verified = True
                verify_tip = "reCAPTCHA anchor/token verified"
                verify_signals = {
                    "anchor_checked": anchor_checked(page),
                    "token_len": len(grecaptcha_response(page)),
                }
            out = {
                "ok": captcha_ok,
                "op": op,
                "platform": platform,
                "branch": captcha_res.get("branch"),
                "grid_solved": captcha_res.get("grid_solved"),
                "grid_rounds": captcha_res.get("grid_rounds", captcha_res.get("rounds", 0)),
                "anchor_checked": captcha_res.get("anchor_checked") or anchor_checked(page),
                "token_len": len(grecaptcha_response(page)),
            }
            if captcha_res.get("last_error"):
                out["grid_error"] = captcha_res["last_error"]
            if post_click_mode:
                out["post_click_mode"] = post_click_mode
            if verified is not None:
                out["verified"] = verified
                out["verify_tip"] = (verify_tip or "").strip()[:300]
                if verify_signals:
                    out["verify_signals"] = verify_signals
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "yidun-click":
            from yidun_click import solve_yidun_text_click, is_yidun_success
            platform = kw["platform"]
            click_res = solve_yidun_text_click(
                page,
                platform,
                captcha_type=click_captcha_type,
                widget_selector=widget_sel,
                auto_trigger=not no_auto_trigger,
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
            )
            ok = bool(click_res.get("ok")) or is_yidun_success(page, widget_sel)
            verified = None
            verify_tip = None
            if success_selector:
                try:
                    page.wait_for_selector(success_selector, state="visible", timeout=8000)
                    verified = True
                    verify_tip = (page.locator(success_selector).first.inner_text(timeout=2000) or "")[:300]
                except Exception:
                    verified = False
            elif ok:
                verified = True
                verify_tip = "yidun text-click passed"
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "click_rounds": click_res.get("rounds", 0),
                "instruction": click_res.get("instruction", ""),
                "points": click_res.get("points", []),
                "yidun_success": is_yidun_success(page, widget_sel),
            }
            if click_res.get("last_error"):
                out["click_error"] = click_res["last_error"]
            if verified is not None:
                out["verified"] = verified
                out["verify_tip"] = (verify_tip or "").strip()[:300]
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "yidun-slide":
            from yidun_slide import solve_yidun_slide
            from yidun_click import is_yidun_success
            platform = kw["platform"]
            slide_res = solve_yidun_slide(
                page,
                platform,
                captcha_type=click_captcha_type,
                widget_selector=widget_sel,
                auto_trigger=not no_auto_trigger,
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
            )
            ok = bool(slide_res.get("ok")) or is_yidun_success(page, widget_sel)
            verified = True if ok else None
            verify_tip = "yidun slide passed" if ok else None
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "slide_rounds": slide_res.get("rounds", 0),
                "offset": slide_res.get("offset", 0),
                "yidun_success": is_yidun_success(page, widget_sel),
            }
            if slide_res.get("last_error"):
                out["slide_error"] = slide_res["last_error"]
            if verified is not None:
                out["verified"] = verified
                out["verify_tip"] = verify_tip
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "jd-jcap-slide":
            from jd_jcap_slide import is_jd_captcha_success, solve_jd_jcap_slide
            platform = kw["platform"]
            slide_res = solve_jd_jcap_slide(
                page,
                platform,
                captcha_type=click_captcha_type,
                widget_selector=widget_sel,
                auto_trigger=not no_auto_trigger,
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
                login_user=kw.get("jd_login_user"),
                login_pass=kw.get("jd_login_pass"),
            )
            ok = bool(slide_res.get("ok"))
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "slide_rounds": slide_res.get("rounds", 0),
                "offset": slide_res.get("offset", 0),
                "jcap_success": ok,
            }
            if slide_res.get("last_error"):
                out["slide_error"] = slide_res["last_error"]
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "icon-click":
            from icon_click import solve_icon_click
            from yidun_click import is_yidun_success
            platform = kw["platform"]
            icon_res = solve_icon_click(
                page,
                platform,
                provider_name=click_provider,
                captcha_type=click_captcha_type,
                widget_selector=widget_sel,
                auto_trigger=not no_auto_trigger,
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
            )
            prov = icon_res.get("provider", click_provider)
            ok = bool(icon_res.get("ok"))
            if prov == "yidun":
                ok = ok or is_yidun_success(page, widget_sel)
            verified = True if ok else None
            verify_tip = "icon-click passed" if ok else None
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "click_provider": prov,
                "click_rounds": icon_res.get("rounds", 0),
                "instruction": icon_res.get("instruction", ""),
                "points": icon_res.get("points", []),
                "captcha_success": ok,
            }
            if prov == "yidun":
                out["yidun_success"] = is_yidun_success(page, widget_sel)
            if icon_res.get("last_error"):
                out["click_error"] = icon_res["last_error"]
            if verified is not None:
                out["verified"] = verified
                out["verify_tip"] = verify_tip
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "jd-login-captcha":
            from jd_login_captcha import solve_jd_login_captcha
            platform = kw["platform"]
            demo_res = solve_jd_login_captcha(
                page,
                platform,
                widget_selector=widget_sel,
                auto_trigger=not no_auto_trigger,
                login_user=kw.get("jd_login_user"),
                login_pass=kw.get("jd_login_pass"),
                track_captcha_type=kw.get("track_captcha_type"),
                rotate_captcha_type=kw.get("rotate_captcha_type"),
                slide_captcha_type=kw.get("slide_captcha_type") or click_captcha_type,
                track_width=float(kw.get("track_width", 300)),
                full_angle=float(kw.get("full_angle", 360)),
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
            )
            ok = bool(demo_res.get("ok"))
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "panel_seen": demo_res.get("panel_seen", False),
                "category": demo_res.get("category"),
                "detection": demo_res.get("detection"),
                "rounds": demo_res.get("rounds", 0),
            }
            for key in ("points", "angle", "offset", "captcha_type", "last_error"):
                if demo_res.get(key) is not None:
                    out[key] = demo_res[key]
            if demo_res.get("last_error"):
                out["solve_error"] = demo_res["last_error"]
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "track":
            if is_dp:
                raise SystemExit("--op track 暂不支持 drissionpage 后端，请用 playwright 或 cloak")
            from track_draw import is_track_success, solve_track_draw
            platform = kw["platform"]
            img_sel = kw["captcha_img_selector"]
            track_type = kw.get("track_captcha_type") or click_captcha_type or 3002
            track_res = solve_track_draw(
                page,
                platform,
                captcha_img_selector=img_sel,
                captcha_type=track_type,
                widget_selector=widget_sel,
                success_selector=success_selector,
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
                wait_visible=not no_auto_trigger,
            )
            ok = bool(track_res.get("ok")) or is_track_success(
                page, img_sel, widget_sel, success_selector,
            )
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "track_rounds": track_res.get("rounds", 0),
                "points": track_res.get("points", []),
                "captcha_type": track_res.get("captcha_type"),
                "track_success": ok,
            }
            if track_res.get("last_error"):
                out["track_error"] = track_res["last_error"]
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "rotate-captcha":
            if is_dp:
                raise SystemExit("--op rotate-captcha 暂不支持 drissionpage 后端，请用 playwright 或 cloak")
            from rotate_captcha import is_rotate_success, solve_rotate_captcha
            platform = kw["platform"]
            img_sel = kw["captcha_img_selector"]
            handle_sel = kw["handle_selector"]
            rotate_type = kw.get("rotate_captcha_type") or click_captcha_type
            rotate_res = solve_rotate_captcha(
                page,
                platform,
                captcha_img_selector=img_sel,
                handle_selector=handle_sel,
                captcha_type=rotate_type,
                widget_selector=widget_sel,
                success_selector=success_selector,
                track_width=float(kw.get("track_width", 300)),
                full_angle=float(kw.get("full_angle", 360)),
                max_rounds=int(click_max_rounds),
                humanize_factor=float(humanize_factor),
                wait_visible=not no_auto_trigger,
            )
            ok = bool(rotate_res.get("ok")) or is_rotate_success(
                page, img_sel, widget_sel, success_selector,
            )
            out = {
                "ok": ok,
                "op": op,
                "platform": platform,
                "rotate_rounds": rotate_res.get("rounds", 0),
                "angle": rotate_res.get("angle", 0),
                "captcha_type": rotate_res.get("captcha_type"),
                "rotate_success": ok,
            }
            if rotate_res.get("last_error"):
                out["rotate_error"] = rotate_res["last_error"]
            print(json.dumps(out, ensure_ascii=False))
            if hold_seconds and not headless:
                time.sleep(hold_seconds)
            return

        elif op == "token":
            res = solve_token_via_cli(kw["platform"], kw["sitekey"], kw["url"])
            token = res.get("token")
            if not token:
                raise RuntimeError(f"平台未返回 token: {res}")
            if is_dp:
                page.run_js(
                    """(tok)=>{const s=['g-recaptcha-response','h-captcha-response','cf-turnstile-response'];
                    for(const id of s){const n=document.getElementById(id); if(n){n.value=tok;}} }""",
                    token,
                )
            else:
                hits = _pw_token(page, token)
                if not hits:
                    # 兜底：写入主文档及 iframe 内 textarea
                    page.evaluate(
                        """(tok) => {
                            const setter = Object.getOwnPropertyDescriptor(
                                window.HTMLTextAreaElement.prototype, 'value').set;
                            let n = 0;
                            for (const ta of document.querySelectorAll('textarea')) {
                                if (/recaptcha|captcha|turnstile/i.test(ta.name + ta.id)) {
                                    setter.call(ta, tok);
                                    ta.dispatchEvent(new Event('input', {bubbles: true}));
                                    n++;
                                }
                            }
                            return n;
                        }""",
                        token,
                    )
            verified = None
            verify_tip = None
            human_sleep(0.5, 1.0)
            if post_click and not is_dp:
                try:
                    page.wait_for_function(
                        """() => {
                            if (window.grecaptcha && typeof window.grecaptcha.getResponse === 'function') {
                                const r = window.grecaptcha.getResponse();
                                if (r && r.length > 20) return true;
                            }
                            for (const ta of document.querySelectorAll('textarea[name="g-recaptcha-response"]')) {
                                if ((ta.value || '').length > 20) return true;
                            }
                            return false;
                        }""",
                        timeout=5000,
                    )
                except Exception:
                    pass
                page.locator(post_click).first.click()
                human_sleep(1.0, 2.0)
            if success_selector and not is_dp:
                verified, verify_tip, verify_signals = _verify_submit_success(
                    page, success_selector=success_selector, timeout_ms=25000,
                )
            out = {"ok": True, "token_injected": True, "platform": kw["platform"]}
            if verified is not None:
                out["verified"] = verified
                out["verify_tip"] = (verify_tip or "").strip()[:300]
                if verify_signals:
                    out["verify_signals"] = verify_signals
            print(json.dumps(out, ensure_ascii=False))
            return

        else:
            raise SystemExit(f"未知操作: {op}")

        verified = None
        verify_tip = None
        if not is_dp and (verify_gt3 or success_selector):
            if verify_gt3:
                verified, verify_tip = _wait_gt3_success(page)
            elif success_selector:
                try:
                    page.wait_for_selector(success_selector, state="visible", timeout=8000)
                    verified, verify_tip = True, success_selector
                except Exception:
                    verified, verify_tip = False, None

        out = {"ok": True, "op": op, "backend": backend}
        if verified is not None:
            out["verified"] = verified
            out["verify_tip"] = verify_tip
        print(json.dumps(out, ensure_ascii=False))
        if hold_seconds and not headless:
            time.sleep(hold_seconds)
    finally:
        _close_page(page, is_dp=is_dp)
        _close_browser(browser)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def build_argparser():
    p = argparse.ArgumentParser(description="R2 多后端反爬浏览器验证码自动化引擎（Python）")
    p.add_argument("--backend", required=True, choices=["cloak", "drissionpage", "playwright"],
                   help="反爬驱动后端")
    p.add_argument("--op", required=True, choices=["slide", "click", "rotate", "rotate-captcha", "track", "token", "recaptcha-grid", "yidun-click", "yidun-slide", "jd-jcap-slide", "jd-login-captcha", "icon-click"],
                   help="操作类型")
    p.add_argument("--target-url", help="目标页面 URL（slide/click/rotate 用）")
    p.add_argument("--headless", action="store_true", help="无头模式（默认有头，便于观察）")
    p.add_argument("--proxy", help="代理 http://user:pass@host:port 或 socks5://...")
    p.add_argument("--no-humanize", action="store_true", help="关闭拟人化（仅 cloak 用）")
    p.add_argument("--no-stealth", action="store_true",
                   help="关闭通用反检测上下文（调试用；验证码场景不推荐）")
    p.add_argument("--chrome-path", default=None,
                   help="Playwright 使用的 Chrome 路径（默认读 config.json automation.chrome_executable 或环境变量 CHROME_EXECUTABLE）")
    p.add_argument("--wait-selector", help="操作前等待出现的元素选择器")
    p.add_argument("--pre-click", help="操作前先点击的元素选择器（用于需手动弹出验证码浮层的页面）")
    p.add_argument("--post-click", help="token/操作完成后点击的元素（如表单 Submit）")
    p.add_argument("--wait-until", default="domcontentloaded",
                   choices=["domcontentloaded", "load", "networkidle"],
                   help="页面加载等待策略（GT3 建议 networkidle）")
    p.add_argument("--hold-seconds", type=float, default=5, help="有头模式下操作完成后停留秒数（默认 5）")
    p.add_argument("--success-selector", help="操作后等待的成功元素选择器")
    p.add_argument("--verify-gt3", action="store_true", help="极验 GT3：拖拽后检测常见成功 DOM 标志")
    p.add_argument("--wait-manual", action="store_true",
                   help="recaptcha-grid：打开页面后等待手动点击 checkbox（终端 Enter 或 --wait-signal）")
    p.add_argument("--wait-signal", metavar="FILE",
                   help="recaptcha-grid：轮询该文件出现后继续（便于 Agent/外部触发）")
    p.add_argument("--no-auto-anchor", action="store_true",
                   help="recaptcha-grid：不自动点击 checkbox（须配合 --wait-manual/--wait-signal）")
    p.add_argument("--humanize-factor", type=float, default=1.3,
                   help="recaptcha-grid 拟人节奏倍率，越大越慢（默认 1.3）")
    p.add_argument("--grid-max-rounds", type=int, default=15, help="recaptcha-grid 最大识别轮次（含多轮题面）")
    p.add_argument("--grid-confidence", type=float, default=0.5,
                   help="YesCaptcha ReCaptchaV2Classification confidence（3x3 推荐 0.5）")
    p.add_argument("--click-captcha-type", type=int, default=None,
                   help="打码平台 captchaType（yidun/icon/track/rotate-captcha 等）")
    p.add_argument("--click-provider", default="auto",
                   choices=["auto", "yidun"],
                   help="icon-click DOM 提供者（auto=按页面特征自动选择）")
    p.add_argument("--widget-selector", default=None,
                   help="验证码 widget 根选择器（icon-click/yidun 通用）")
    p.add_argument("--yidun-widget-selector", default=None,
                   help="同 --widget-selector（兼容旧参数）")
    p.add_argument("--click-max-rounds", type=int, default=3,
                   help="yidun-click/slide/icon-click 最大识别轮次")
    p.add_argument("--no-auto-trigger", action="store_true",
                   help="不自动等待验证码出现（须手动触发后再跑，或配合 --pre-click）")
    p.add_argument("--jd-login-user", default=None, help="jd-login-captcha/jd-jcap-slide：密码登录账号（也可用环境变量 JD_LOGIN_USER）")
    p.add_argument("--jd-login-pass", default=None, help="jd-login-captcha/jd-jcap-slide：密码登录密码（也可用环境变量 JD_LOGIN_PASS）")
    p.add_argument("--track-captcha-type", type=int, default=3002,
                   help="轨迹类 captchaType（jd-login-captcha / track，默认 3002）")
    p.add_argument("--rotate-captcha-type", type=int, default=11201,
                   help="旋转类 captchaType（jd-login-captcha，冰拓官方 11201/1120）")
    p.add_argument("--slide-captcha-type", type=int, default=None, help="jd-login-captcha：滑块类 captchaType（默认 1310）")

    # slide
    p.add_argument("--slider-selector", help="滑块元素选择器（slide）")
    p.add_argument("--offset", help="滑块像素距离（slide）")
    # click / track / rotate-captcha
    p.add_argument("--captcha-img-selector", help="验证码图片/画布选择器（click/track/rotate-captcha）")
    p.add_argument("--points", help='相对图片的像素坐标列表，如 "[[120,80],[200,150]]"（click）')
    # rotate
    p.add_argument("--handle-selector", help="旋转手柄选择器（rotate）")
    p.add_argument("--angle", help="旋转角度（rotate）")
    p.add_argument("--track-width", default="300", help="旋转轨道宽度像素（rotate/rotate-captcha，默认 300）")
    p.add_argument("--full-angle", default="360", help="旋转一圈对应角度（rotate-captcha，默认 360）")
    # token
    p.add_argument("--platform", help="打码平台（token，调 solve.py）")
    p.add_argument("--sitekey", help="站点 sitekey（token）")
    p.add_argument("--url", help="站点 url（token，同 target-url 时也可省略）")
    return p


def main():
    args = build_argparser().parse_args()
    if args.op in ("slide", "click", "rotate") and not args.target_url:
        raise SystemExit(f"--op {args.op} 需要 --target-url")
    if args.op in ("slide", "rotate") and not args.headless:
        # 有头便于观察，不强制
        pass

    kw = {}
    if args.op == "slide":
        if not args.slider_selector or args.offset is None:
            raise SystemExit("--op slide 需要 --slider-selector 和 --offset")
        kw["slider_selector"] = args.slider_selector
        kw["offset"] = args.offset
    elif args.op == "click":
        if not args.captcha_img_selector or not args.points:
            raise SystemExit("--op click 需要 --captcha-img-selector 和 --points")
        kw["captcha_img_selector"] = args.captcha_img_selector
        kw["points"] = args.points
    elif args.op == "rotate":
        if not args.handle_selector or args.angle is None:
            raise SystemExit("--op rotate 需要 --handle-selector 和 --angle")
        kw["handle_selector"] = args.handle_selector
        kw["angle"] = args.angle
        kw["track_width"] = args.track_width
    elif args.op == "token":
        if not (args.platform and args.sitekey):
            raise SystemExit("--op token 需要 --platform 和 --sitekey")
        kw["platform"] = args.platform
        kw["sitekey"] = args.sitekey
        kw["url"] = args.url or args.target_url
        if not kw["url"]:
            raise SystemExit("--op token 需要 --url（或 --target-url）")
    elif args.op == "recaptcha-grid":
        if not args.platform:
            raise SystemExit("--op recaptcha-grid 需要 --platform（当前支持 yescaptcha）")
        if not args.target_url:
            raise SystemExit("--op recaptcha-grid 需要 --target-url")
        kw["platform"] = args.platform
    elif args.op == "yidun-slide":
        if not args.platform:
            raise SystemExit("--op yidun-slide 需要 --platform（当前推荐 bingtop）")
        if not args.target_url:
            raise SystemExit("--op yidun-slide 需要 --target-url")
        kw["platform"] = args.platform
    elif args.op == "jd-jcap-slide":
        if not args.platform:
            raise SystemExit("--op jd-jcap-slide 需要 --platform（当前推荐 bingtop）")
        if not args.target_url:
            raise SystemExit("--op jd-jcap-slide 需要 --target-url")
        kw["platform"] = args.platform
        import os
        kw["jd_login_user"] = args.jd_login_user or os.environ.get("JD_LOGIN_USER")
        kw["jd_login_pass"] = args.jd_login_pass or os.environ.get("JD_LOGIN_PASS")
    elif args.op == "jd-login-captcha":
        if not args.platform:
            raise SystemExit("--op jd-login-captcha 需要 --platform（推荐 bingtop）")
        if not args.target_url:
            raise SystemExit("--op jd-login-captcha 需要 --target-url")
        kw["platform"] = args.platform
        import os
        kw["jd_login_user"] = args.jd_login_user or os.environ.get("JD_LOGIN_USER")
        kw["jd_login_pass"] = args.jd_login_pass or os.environ.get("JD_LOGIN_PASS")
        kw["track_captcha_type"] = args.track_captcha_type
        kw["rotate_captcha_type"] = args.rotate_captcha_type
        kw["slide_captcha_type"] = args.slide_captcha_type
        kw["track_width"] = args.track_width
        kw["full_angle"] = args.full_angle
    elif args.op == "yidun-click":
        if not args.platform:
            raise SystemExit("--op yidun-click 需要 --platform（当前推荐 bingtop）")
        if not args.target_url:
            raise SystemExit("--op yidun-click 需要 --target-url")
        kw["platform"] = args.platform
    elif args.op == "icon-click":
        if not args.platform:
            raise SystemExit("--op icon-click 需要 --platform（当前推荐 bingtop）")
        if not args.target_url:
            raise SystemExit("--op icon-click 需要 --target-url")
        kw["platform"] = args.platform
    elif args.op == "track":
        if not args.platform:
            raise SystemExit("--op track 需要 --platform（轨迹绘制推荐 bingtop + captchaType 3002）")
        if not args.target_url:
            raise SystemExit("--op track 需要 --target-url")
        if not args.captcha_img_selector:
            raise SystemExit("--op track 需要 --captcha-img-selector（验证码绘制区域）")
        kw["platform"] = args.platform
        kw["captcha_img_selector"] = args.captcha_img_selector
        kw["track_captcha_type"] = args.track_captcha_type
    elif args.op == "rotate-captcha":
        if not args.platform:
            raise SystemExit("--op rotate-captcha 需要 --platform（旋转推荐 bingtop + captchaType 11201）")
        if not args.target_url:
            raise SystemExit("--op rotate-captcha 需要 --target-url")
        if not args.captcha_img_selector:
            raise SystemExit("--op rotate-captcha 需要 --captcha-img-selector")
        if not args.handle_selector:
            raise SystemExit("--op rotate-captcha 需要 --handle-selector（旋转拖拽手柄）")
        kw["platform"] = args.platform
        kw["captcha_img_selector"] = args.captcha_img_selector
        kw["handle_selector"] = args.handle_selector
        kw["track_width"] = args.track_width
        kw["full_angle"] = args.full_angle
        kw["rotate_captcha_type"] = args.rotate_captcha_type

    run(
        backend=args.backend,
        op=args.op,
        target_url=args.target_url or (args.url if args.op in ("token",) else ""),
        headless=args.headless,
        proxy=args.proxy,
        humanize=not args.no_humanize,
        wait_selector=args.wait_selector,
        pre_click=args.pre_click,
        hold_seconds=args.hold_seconds,
        chrome_path=args.chrome_path if args.backend == "playwright" else None,
        wait_until=args.wait_until,
        success_selector=args.success_selector,
        verify_gt3=args.verify_gt3,
        post_click=args.post_click,
        wait_manual=args.wait_manual or bool(args.wait_signal),
        wait_signal=args.wait_signal,
        grid_max_rounds=args.grid_max_rounds,
        grid_confidence=args.grid_confidence,
        auto_anchor=not args.no_auto_anchor,
        humanize_factor=args.humanize_factor,
        click_captcha_type=args.click_captcha_type,
        yidun_widget_selector=args.yidun_widget_selector,
        widget_selector=args.widget_selector,
        click_provider=args.click_provider,
        click_max_rounds=args.click_max_rounds,
        no_auto_trigger=args.no_auto_trigger,
        stealth=not args.no_stealth,
        **kw,
    )


if __name__ == "__main__":
    main()
