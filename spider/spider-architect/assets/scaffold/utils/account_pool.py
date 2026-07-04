"""账号池 — 基于 RedisDB Hash + Set。"""

from __future__ import annotations

import json
from typing import Any

from config import settings
from utils.db.redis_client import get_redis


class AccountPool:
    """
    Redis 结构：
      {prefix}:accounts:active  — Set，存 account_id
      {prefix}:accounts:detail  — Hash，account_id → JSON
      {prefix}:accounts:banned  — Set，封禁账号
    """

    def __init__(self, prefix: str | None = None):
        self.redis = get_redis()
        self.prefix = prefix or settings.REDIS_KEY_PREFIX
        self.key_active = f"{self.prefix}:accounts:active"
        self.key_detail = f"{self.prefix}:accounts:detail"
        self.key_banned = f"{self.prefix}:accounts:banned"

    def register(self, account_id: str, payload: dict[str, Any]) -> None:
        """注册账号到池。"""
        payload.setdefault("status", "active")
        self.redis.sadd(self.key_active, account_id)
        self.redis.hset(self.key_detail, account_id, json.dumps(payload, ensure_ascii=False))

    def get_account(self, pop: bool = False) -> dict[str, Any] | None:
        """随机获取账号。pop=True 时使用 sget(is_pop=True)。"""
        ids = self.redis.sget(self.key_active, count=1, is_pop=pop)
        if not ids or not ids[0]:
            return None
        account_id = ids[0]
        raw = self.redis.hget(self.key_detail, account_id)
        if not raw:
            self.mark_invalid(account_id)
            return None
        data = json.loads(raw)
        data["account_id"] = account_id
        return data

    def get_cookie_header(self) -> str:
        account = self.get_account(pop=False)
        if not account:
            return ""
        return account.get("cookie", "")

    def mark_invalid(self, account_id: str) -> None:
        """失效回收：从 active 移除，加入 banned。"""
        self.redis.srem(self.key_active, account_id)
        self.redis.sadd(self.key_banned, account_id)
        raw = self.redis.hget(self.key_detail, account_id)
        if raw:
            payload = json.loads(raw)
            payload["status"] = "banned"
            self.redis.hset(
                self.key_detail, account_id, json.dumps(payload, ensure_ascii=False)
            )

    def list_active_ids(self) -> list:
        """调试：hkeys detail 与 active set 交叉验证。"""
        return self.redis.sget(self.key_active, count=self.redis.sget_count(self.key_active), is_pop=False)

    # --- SKILL HOOK: account_login ---
    # Cookie 链/登录态还原请转交 web-protocol-recovery 或 rs-reverse
    def refresh_account(self, account_id: str) -> dict[str, Any]:
        raise NotImplementedError(
            "请通过 web-protocol-recovery / rs-reverse 实现登录态刷新后调用 register()"
        )

    # --- SKILL HOOK: playwright_state ---
    # L4+ 浏览器取态请转交 web-protocol-recovery
    def import_from_playwright(self, account_id: str, cookie: str, **meta: Any) -> None:
        self.register(account_id, {"cookie": cookie, "source": "playwright", **meta})


account_pool = AccountPool() if settings.ACCOUNT_POOL_ENABLE else None
