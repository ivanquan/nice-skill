"""TaskSpider 模板 — 复杂调度/周期任务/动态下发。"""

import feapder

from config import settings


class MainSpider(feapder.TaskSpider):
    __custom_setting__ = dict(
        REDISDB_IP_PORTS=settings.REDISDB_IP_PORTS,
        REDISDB_USER_PASS=settings.REDISDB_USER_PASS,
        REDISDB_DB=settings.REDISDB_DB,
        SPIDER_THREAD_COUNT=settings.SPIDER_THREAD_COUNT,
        SPIDER_MAX_RETRY_TIMES=settings.SPIDER_MAX_RETRY_TIMES,
        REQUEST_TIMEOUT=settings.REQUEST_TIMEOUT,
    )

    def add_task(self):
        """TaskSpider 入口：在此添加/下发任务。"""
        yield feapder.Task(
            priority=1,
            url="{START_URL}",
            callback=self.parse,
        )

    def parse(self, task, response):
        # --- SKILL HOOK: sign_helper ---
        # 动态签名请转交 dy-ab-pure 或 web-protocol-recovery
        # --- END SKILL HOOK ---

        if response.status_code != 200:
            self.logger.warning("非 200: %s", response.status_code)
            return

        # TODO: 解析；可 yield feapder.Task 动态下发子任务
        self.logger.info("task parsed %s", task.url)


if __name__ == "__main__":
    MainSpider(task_table="{PROJECT_NAME}.task").start()
