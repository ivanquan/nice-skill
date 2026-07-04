"""BatchSpider 模板 — 海量/分布式/断点续传。"""

import feapder

from config import settings


class MainSpider(feapder.BatchSpider):
    __custom_setting__ = dict(
        REDISDB_IP_PORTS=settings.REDISDB_IP_PORTS,
        REDISDB_USER_PASS=settings.REDISDB_USER_PASS,
        REDISDB_DB=settings.REDISDB_DB,
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
        # --- END SKILL HOOK ---

        if response.status_code != 200:
            self.logger.warning("非 200: %s", response.status_code)
            return

        # TODO: 解析并 yield Item；BatchSpider 自动持久去重
        self.logger.info("batch parsed %s", request.url)

        # --- SKILL HOOK: env-patch ---
        # Node.js 补环境 sign 请转交 env-patch
        # --- END SKILL HOOK ---


if __name__ == "__main__":
    MainSpider(redis_key="{PROJECT_NAME}:batch").start()
