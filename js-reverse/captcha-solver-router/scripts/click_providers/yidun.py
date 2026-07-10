#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网易易盾图标点选验证码 DOM 提供者（供通用 icon-click 流程调用）。"""

import base64
import io
import time
import urllib.request

from browser_stealth import get_mouse_state, human_move_to
from yidun_click import (
    click_yidun_points,
    find_yidun_widget,
    install_yidun_front_hook,
    is_yidun_success,
    read_yidun_instruction,
    reload_yidun_challenge,
    trigger_yidun,
    wait_yidun_image_ready,
    yidun_panel_visible,
)
from recaptcha_grid import HumanPacer


def _png_dims(png_bytes):
    """从 PNG 字节读取宽高，用于与打码平台坐标对齐。"""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        return float(img.size[0]), float(img.size[1])
    except Exception:
        return 0.0, 0.0


def _screenshot_to_image_b64(png_bytes):
    """将 Playwright PNG 截图转为标准图片 base64（原始 PNG 字节，无 data-uri 前缀）。"""
    if len(png_bytes) < 100:
        raise RuntimeError("截图字节过小")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    w, h = _png_dims(png_bytes)
    return b64, w, h


class YidunIconProvider:
    """易盾图标点选：题面为图标提示图，在背景图中按序点击相同图标。"""

    name = "yidun"

    def __init__(self, page, widget_selector=None):
        """绑定页面与可选 widget 选择器。"""
        self.page = page
        self.widget_selector = widget_selector or ".yidun--icon_point, .yidun--icon, .yidun"
        self._bg_coord_wh = None

    def prepare(self):
        """安装网络 hook 等前置逻辑。"""
        install_yidun_front_hook(self.page)

    def _hover_float_bar(self, pacer):
        """触发式 float widget：鼠标移入验证条以展开面板。"""
        root = find_yidun_widget(self.page, self.widget_selector)
        if not root:
            return False
        try:
            cls = root.get_attribute("class") or ""
            if "yidun--float" not in cls:
                return False
            ctrl = root.locator(".yidun_control").first
            if not ctrl.count():
                return False
            box = ctrl.bounding_box()
            if not box:
                return False
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            human_move_to(self.page, cx, cy, state=get_mouse_state(self.page))
            pacer.pause(0.9, 1.6)
            return True
        except Exception:
            return False

    def trigger(self, pacer):
        """点击/移入验证条展开面板。"""
        root = find_yidun_widget(self.page, self.widget_selector)
        if root:
            try:
                root.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                pass
        self._hover_float_bar(pacer)
        return trigger_yidun(self.page, pacer, self.widget_selector)

    def panel_visible(self):
        """面板是否可见（含 float 展开态）。"""
        if yidun_panel_visible(self.page, self.widget_selector):
            return True
        root = find_yidun_widget(self.page, self.widget_selector)
        if not root:
            return False
        try:
            return root.evaluate(
                """(el) => {
                    const panel = el.querySelector('.yidun_panel');
                    const bg = el.querySelector('.yidun_bgimg');
                    if (panel && panel.offsetParent !== null) return true;
                    if (bg && bg.offsetParent !== null) {
                        const r = bg.getBoundingClientRect();
                        return r.width > 60 && r.height > 60;
                    }
                    return false;
                }"""
            )
        except Exception:
            return False

    def wait_ready(self, pacer, timeout_sec=15):
        """等待图标点选面板与背景图、提示图就绪。"""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if not self.panel_visible():
                self._hover_float_bar(pacer)
                trigger_yidun(self.page, pacer, self.widget_selector)
            if self.panel_visible():
                wait_yidun_image_ready(
                    self.page, timeout_sec=6, pacer=pacer, widget_selector=self.widget_selector,
                )
                pacer.pause(0.6, 1.0)
                if self.read_hint_b64():
                    return True
            pacer.pause(0.45, 0.8)
        return self.panel_visible()

    def read_instruction(self):
        """读取题面说明文字。"""
        return read_yidun_instruction(self.page, self.widget_selector)

    def _hint_element(self):
        """定位题面图标提示图元素。"""
        root = find_yidun_widget(self.page, self.widget_selector)
        if not root:
            return None
        for sel in (".yidun_tips__answer .yidun_tips__img", ".yidun_tips__img"):
            loc = root.locator(sel).first
            if loc.count():
                try:
                    if loc.is_visible():
                        return loc
                except Exception:
                    continue
        return None

    def read_hint_b64(self):
        """读取题面图标提示图 base64（优先元素截图，与背景图 URL 解耦）。"""
        loc = self._hint_element()
        if loc:
            try:
                png = loc.screenshot(timeout=8000)
                if len(png) > 200:
                    b64, _, _ = _screenshot_to_image_b64(png)
                    print(f"[icon-click/yidun] 提示图截图 ok bytes={len(png)} b64_len={len(b64)}", flush=True)
                    return b64
            except Exception as exc:
                print(f"[icon-click/yidun] 提示图截图失败: {exc}", flush=True)
        return ""

    def capture_bg_b64(self):
        """截取背景验证码图（.yidun_bgimg 容器截图），返回 (b64, selector, coord_wh)。"""
        root = find_yidun_widget(self.page, self.widget_selector)
        if not root:
            raise RuntimeError("未找到易盾 widget")
        bg_loc = root.locator(".yidun_bgimg").first
        if not bg_loc.count() or not bg_loc.is_visible():
            raise RuntimeError("背景图区域不可见")
        png = bg_loc.screenshot(timeout=10000)
        if len(png) < 500:
            raise RuntimeError("背景图截图过小")
        b64, cw, ch = _screenshot_to_image_b64(png)
        box = bg_loc.bounding_box() or {}
        if cw <= 0:
            cw = float(box.get("width") or 320)
        if ch <= 0:
            ch = float(box.get("height") or 160)
        self._bg_coord_wh = (cw, ch)
        print(
            f"[icon-click/yidun] 背景图截图 ok bytes={len(png)} b64_len={len(b64)} coord={cw:.0f}x{ch:.0f}",
            flush=True,
        )
        return b64, ".yidun_bgimg", (cw, ch)

    def expected_click_count(self, hint_b64):
        """估算需点击次数。"""
        instruction = self.read_instruction() or ""
        nums = __import__("re").findall(r"(\d+)\s*个", instruction)
        if nums:
            return max(1, int(nums[0]))
        return 3 if hint_b64 else 1

    def click_points(self, img_selector, points, pacer, natural_wh=None):
        """拟人点击坐标列表（坐标系与上传给打码平台的背景截图一致）。"""
        click_yidun_points(
            self.page, img_selector, points, pacer,
            self.widget_selector,
            coord_image_wh=self._bg_coord_wh or natural_wh,
        )

    def is_success(self):
        """是否验证通过。"""
        return is_yidun_success(self.page, self.widget_selector)

    def reload(self, pacer):
        """刷新挑战。"""
        return reload_yidun_challenge(self.page, pacer, self.widget_selector)

    def wait_hint(self, pacer, timeout_sec=8):
        """限时等待图标提示图出现。"""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if not self.panel_visible():
                self._hover_float_bar(pacer)
            hint = self.read_hint_b64()
            if hint:
                return self.read_instruction(), hint
            pacer.pause(0.35, 0.55)
        return self.read_instruction(), self.read_hint_b64()
