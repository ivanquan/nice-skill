"""AirSpider 模板 — 轻量单机，无 Redis。"""

import feapder

from config import settings


class MainSpider(feapder.AirSpider):
    __custom_setting__ = dict(
        SPIDER_THREAD_COUNT=settings.SPIDER_THREAD_COUNT,
        SPIDER_MAX_RETRY_TIMES=settings.SPIDER_MAX_RETRY_TIMES,
        REQUEST_TIMEOUT=settings.REQUEST_TIMEOUT,
    )

    def start_requests(self):
        yield feapder.Request(
            url="{START_URL}",
            callback=self.parse,
        )

    def parse(self, request, response):
        # --- SKILL HOOK: sign_helper ---
        # 动态签名请转交 dy-ab-pure 或 web-protocol-recovery
        # from utils.sign_helper import sign_request
        # --- END SKILL HOOK ---

        if response.status_code != 200:
            self.logger.warning("非 200: %s", response.status_code)
            return

        # 账号 Cookie（Redis 账号池）
        # from utils.account_pool import account_pool
        # cookie = account_pool.get_cookie_header() if account_pool else ""

        # --- SKILL HOOK: mysql_storage / mongo_storage ---
        # 结构化字段 → pipelines/mysql_pipeline.py (add_smart)
        # 原始响应   → pipelines/mongo_pipeline.py (mongo.add)
        item = {
            "url": request.url,
            "domain": settings.TARGET_DOMAIN,
            "status_code": response.status_code,
            # "title": "...",  # 解析后结构化字段
            "_raw": {
                "url": request.url,
                "status_code": response.status_code,
                "headers": dict(response.headers) if response.headers else {},
                "body_preview": response.text[:2000] if response.text else "",
            },
        }
        yield item
        # --- END SKILL HOOK ---

        # --- SKILL HOOK: captcha ---
        # 滑块/验证码请转交 captcha-slide-reverse
        # --- END SKILL HOOK ---


if __name__ == "__main__":
    MainSpider().start()
