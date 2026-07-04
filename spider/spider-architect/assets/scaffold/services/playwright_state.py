"""Playwright 取态服务占位 — L4+ 混合模式按需创建。"""

# --- SKILL HOOK: playwright_state ---
# 浏览器取态/Cookie 链请转交 web-protocol-recovery
# --- END SKILL HOOK ---


def export_state_to_cache(output_path: str = "crawler_cache/playwright_state.json") -> str:
    """登录/过 challenge 后导出 Cookie/Storage 到 crawler_cache/。"""
    raise NotImplementedError("请通过 web-protocol-recovery 实现 Playwright 取态逻辑")
