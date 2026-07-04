"""sign_helper 占位 — L3+ 项目按需创建。"""

# --- SKILL HOOK: sign_helper ---
# 动态签名生成请转交：
#   - 抖音 a_bogus → dy-ab-pure
#   - 通用协议 sign → web-protocol-recovery
# --- END SKILL HOOK ---


def sign_request(url: str, params: dict | None = None, headers: dict | None = None) -> tuple[str, dict, dict]:
    """返回 (signed_url, params, headers)。实现由逆向 Skill 产出。"""
    raise NotImplementedError("请通过 dy-ab-pure 或 web-protocol-recovery 实现签名逻辑")
