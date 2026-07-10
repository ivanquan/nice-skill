# -*- coding: utf-8 -*-
"""图标点选验证码 DOM 提供者注册表（厂商可插拔）。"""

from click_providers.yidun import YidunIconProvider

PROVIDER_REGISTRY = {
    "yidun": YidunIconProvider,
}


def resolve_icon_provider(name, page, widget_selector=None):
    """按名称或页面特征解析图标点选提供者。"""
    if name and name != "auto":
        cls = PROVIDER_REGISTRY.get(name)
        if not cls:
            raise RuntimeError(f"未知 click-provider: {name}，可选: {list(PROVIDER_REGISTRY)}")
        return cls(page, widget_selector)

    if page.locator(".yidun--icon_point, .yidun--icon").count():
        return YidunIconProvider(page, widget_selector)
    if widget_selector and page.locator(widget_selector).count():
        return YidunIconProvider(page, widget_selector)

    raise RuntimeError(
        "无法自动识别图标点选提供者，请显式传 --click-provider yidun 或 --widget-selector"
    )
