"""代理中间件 — RedisDB 代理池 + 第三方代理 + 失效回收。"""

from __future__ import annotations

import feapder
import requests

from config import settings
from utils.db.redis_client import get_redis


class ProxyMiddleware:
    """
    Redis 结构：
      {prefix}:proxies:active — 可用代理 Set
      {prefix}:proxies:dead   — 失效代理 Set
    """

    def __init__(self):
        self.enabled = settings.PROXY_ENABLE
        self.provider = settings.PROXY_PROVIDER
        self.redis = get_redis() if self.enabled else None
        self.prefix = settings.REDIS_KEY_PREFIX
        self.key_active = f"{self.prefix}:proxies:active"
        self.key_dead = f"{self.prefix}:proxies:dead"

    def _fetch_third_party_proxy(self) -> str | None:
        """从 SmartProxy / ScraperAPI 获取代理 URL。"""
        if self.provider == "smartproxy" and settings.SMARTPROXY_GATEWAY_URL:
            return settings.SMARTPROXY_GATEWAY_URL
        if self.provider == "scraperapi" and settings.SCRAPERAPI_KEY:
            key = settings.SCRAPERAPI_KEY
            return f"http://scraperapi:{key}@proxy-server.scraperapi.com:8001"
        if self.provider == "api" and settings.PROXY_POOL_API:
            resp = requests.get(settings.PROXY_POOL_API, timeout=10)
            resp.raise_for_status()
            # 按实际 API 格式解析；示例取首行
            line = resp.text.strip().splitlines()[0]
            return line if line.startswith("http") else f"http://{line}"
        return None

    def get_proxy(self) -> str | None:
        if not self.enabled:
            return None

        # 优先 Redis 池
        if self.provider == "redis" or self.redis.sget_count(self.key_active):
            proxies = self.redis.sget(self.key_active, count=1, is_pop=False)
            if proxies and proxies[0]:
                return proxies[0]

        # 第三方拉取并回填 Redis
        proxy = self._fetch_third_party_proxy()
        if proxy and self.redis:
            self.redis.sadd(self.key_active, proxy)
        return proxy

    def mark_dead(self, proxy: str) -> None:
        """代理失效：移出 active，加入 dead。"""
        if not self.redis or not proxy:
            return
        self.redis.srem(self.key_active, proxy)
        self.redis.sadd(self.key_dead, proxy)

    def process_request(self, request: feapder.Request) -> feapder.Request:
        proxy = self.get_proxy()
        if proxy:
            request.proxies = {"http": proxy, "https": proxy}
            request.meta["proxy"] = proxy
        return request

    def process_response(self, request: feapder.Request, response) -> feapder.Response:
        proxy = request.meta.get("proxy")
        if proxy and response.status_code in (403, 407, 429, 502, 503):
            self.mark_dead(proxy)
        return response


proxy_middleware = ProxyMiddleware()
