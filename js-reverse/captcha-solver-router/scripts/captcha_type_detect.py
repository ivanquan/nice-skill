#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用验证码类型识别：根据页面文案与 DOM 结构判断 slide / track / rotate。

适用于京东 JCAP 等同一浮层可能轮换多种题型的场景。
"""

import json

from bingtop_types import resolve_captcha_type

DEFAULT_WIDGET = (
    "#captcha_modal, .captcha_modal_pc, .captcha_drop, "
    "#slideAuthCode, .slide-authCode-wraper, .JDValidate-wrap"
)

# 各类型文案信号（优先级：轨迹 > 旋转 > 滑块）
TRACK_HINTS = ("轨迹", "绘制", "按图中", "画线", "gesture")
ROTATE_HINTS = ("使图片为正", "图片为正", "旋转", "转动", "角度", "摆正", "rotate")
SLIDE_HINTS = ("拼图", "向右拖动", "拖动滑块完成", "缺口", "完成拼图")

# 通用 DOM 选择器（京东新版 captcha_modal + 旧版 JCAP）
IMG_SELECTORS = [
    ".captcha_body .slot-content img",
    ".slot-content img",
    ".captcha_body img",
    ".JDJRV-bigimg img",
    ".JDJRV-bigimg canvas",
    ".JDJRV-bigimg",
    ".jdcap-bigimg img",
    ".jdcap-bigimg",
    ".captcha-img img",
    ".captcha-img canvas",
    ".captcha-img",
]
SLICE_SELECTORS = [
    ".JDJRV-smallimg img",
    ".jdcap-smallimg img",
    ".captcha-slider img",
]
HANDLE_SELECTORS = [
    "#slider-div",
    ".captcha_footer .drag-box img",
    ".drag-box img",
    "#slide_path",
    ".JDJRV-slide-btn",
    ".JDJRV-slide-inner",
    ".JDJRV-slide",
    ".jdcap-slide-btn",
    ".rotate-handle",
    ".captcha-slider-btn",
]

_DETECT_JS = """
(payload) => {
    const {
        widgetSels,
        trackHints,
        rotateHints,
        slideHints,
        imgSels,
        sliceSels,
        handleSels,
    } = payload || {};
    const pickVisible = (selectors) => {
        for (const s of selectors) {
            const el = document.querySelector(s);
            if (!el) continue;
            const r = el.getBoundingClientRect();
            if (r.width > 8 && r.height > 8) return s;
        }
        return null;
    };
    const isVisible = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return false;
        const r = el.getBoundingClientRect();
        const st = window.getComputedStyle(el);
        return r.width > 5 && r.height > 5 && st.visibility !== 'hidden' && st.display !== 'none';
    };

    const widgets = (widgetSels || '').split(',').map(s => s.trim()).filter(Boolean);
    let root = null;
    const modal = document.querySelector('#captcha_modal, .captcha_modal_pc');
    if (modal) {
        const mr = modal.getBoundingClientRect();
        if (mr.width > 50 && mr.height > 50) root = modal;
    }
    if (!root) {
        for (const s of widgets) {
            if (isVisible(s)) { root = document.querySelector(s); break; }
        }
    }
    if (!root) {
        for (const s of widgets) {
            const el = document.querySelector(s);
            if (el) { root = el; break; }
        }
    }

    const tipEl = document.querySelector('#local_tip, .captcha_footer .tip_text');
    const modalText = ((modal && modal.innerText) || '').replace(/\\s+/g, ' ');
    const tipText = ((tipEl && tipEl.innerText) || '').replace(/\\s+/g, ' ');
    const text = (modalText || tipText || (root && root.innerText) || document.body.innerText || '').replace(/\\s+/g, ' ');
    const snippet = text.slice(0, 400);
    const hasHint = (hints) => hints.some(h => snippet.includes(h));

    const hasRotateDom = !!document.querySelector(
        '[class*="rotate"], .JDJRV-rotate, .rotate-img, .jdcap-rotate, .slot-content img'
    );
    const sliceVisible = sliceSels.some(s => isVisible(s));
    const handleVisible = handleSels.some(s => isVisible(s));
    const imgSel = pickVisible(imgSels) || pickVisible(imgSels.map(s => s.split(' ')[0]));
    const handleSel = pickVisible(handleSels) || handleSels.join(', ');

    let category = 'unknown';
    let confidence = 'low';
    const evidence = [];

    if (hasHint(trackHints)) {
        category = 'track';
        confidence = 'high';
        evidence.push('text:轨迹绘制提示');
    } else if (hasHint(rotateHints)) {
        category = 'rotate';
        confidence = 'high';
        evidence.push('text:旋转提示');
    } else if (sliceVisible && handleVisible) {
        category = 'slide';
        confidence = 'high';
        evidence.push('dom:滑块块+手柄');
    } else if (sliceVisible) {
        category = 'slide';
        confidence = 'medium';
        evidence.push('dom:滑块块');
    } else if (handleVisible && !sliceVisible) {
        if (hasHint(rotateHints) || /使图片为正|旋转|转动/.test(snippet)) {
            category = 'rotate';
            confidence = hasHint(rotateHints) ? 'high' : 'medium';
            evidence.push(hasHint(rotateHints) ? 'text:旋转提示' : 'dom:手柄无滑块块→旋转');
        } else if (hasHint(slideHints)) {
            category = 'slide';
            confidence = 'medium';
            evidence.push('text:滑块文案');
        } else {
            category = 'track';
            confidence = 'medium';
            evidence.push('dom:手柄无滑块块→倾向轨迹');
        }
    } else if (imgSel && !sliceVisible) {
        if (hasHint(slideHints)) {
            category = 'slide';
            confidence = 'low';
            evidence.push('text:滑块文案但无滑块块DOM');
        } else if (hasHint(rotateHints) || /使图片为正/.test(snippet)) {
            category = 'rotate';
            confidence = 'medium';
            evidence.push('text+dom:主图+旋转文案');
        } else {
            category = 'track';
            confidence = 'medium';
            evidence.push('dom:仅主图区域');
        }
    }

    return {
        category,
        confidence,
        evidence,
        hint_text: snippet.slice(0, 160),
        img_selector: imgSel,
        handle_selector: handleSel,
        slice_visible: sliceVisible,
        handle_visible: handleVisible,
        widget_found: !!root,
        modal_visible: !!(modal && modal.getBoundingClientRect().width > 50),
    };
}
"""


def detect_captcha_category(page, widget_selector=None):
    """
    识别当前页面验证码类型，返回 category / confidence / selectors。
    category: track | rotate | slide | unknown
    """
    widget_sels = widget_selector or DEFAULT_WIDGET
    payload = {
        "widgetSels": widget_sels,
        "trackHints": list(TRACK_HINTS),
        "rotateHints": list(ROTATE_HINTS),
        "slideHints": list(SLIDE_HINTS),
        "imgSels": IMG_SELECTORS,
        "sliceSels": SLICE_SELECTORS,
        "handleSels": HANDLE_SELECTORS,
    }
    try:
        data = page.evaluate(_DETECT_JS, payload)
    except Exception as exc:
        return {
            "category": "unknown",
            "confidence": "low",
            "evidence": [f"evaluate失败: {exc}"],
            "hint_text": "",
            "img_selector": IMG_SELECTORS[0],
            "handle_selector": HANDLE_SELECTORS[0],
        }

    img_sel = data.get("img_selector") or IMG_SELECTORS[0]
    # 轨迹绘制优先截整块绘制区（含 canvas）
    if data.get("category") == "track":
        for cand in (".captcha_body .slot-content", ".captcha_body", ".JDJRV-bigimg", ".jdcap-bigimg", img_sel):
            loc = page.locator(cand).first
            if loc.count():
                try:
                    if loc.is_visible():
                        img_sel = cand
                        break
                except Exception:
                    img_sel = cand
                    break
    elif data.get("category") == "rotate":
        for cand in (".captcha_body .slot-content img", ".slot-content img", img_sel):
            loc = page.locator(cand).first
            if loc.count():
                try:
                    if loc.is_visible():
                        img_sel = cand
                        break
                except Exception:
                    img_sel = cand
                    break

    return {
        "category": data.get("category") or "unknown",
        "confidence": data.get("confidence") or "low",
        "evidence": data.get("evidence") or [],
        "hint_text": data.get("hint_text") or "",
        "img_selector": img_sel,
        "handle_selector": data.get("handle_selector") or HANDLE_SELECTORS[0],
        "slice_visible": bool(data.get("slice_visible")),
        "handle_visible": bool(data.get("handle_visible")),
        "bingtop_captcha_type": resolve_captcha_type(data.get("category") or "unknown"),
    }


def format_detection_log(det):
    """格式化识别结果日志。"""
    return json.dumps(det, ensure_ascii=False)
