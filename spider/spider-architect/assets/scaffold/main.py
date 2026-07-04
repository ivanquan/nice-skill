"""项目启动入口 — 由 spider-architect 生成。"""

from config import settings

if settings.FEAPDER_MODE == "air":
    from spiders.main_spider import MainSpider

    if __name__ == "__main__":
        MainSpider().start()

elif settings.FEAPDER_MODE == "batch":
    from spiders.main_spider import MainSpider

    if __name__ == "__main__":
        MainSpider(redis_key=f"{settings.PROJECT_NAME}:batch").start()

elif settings.FEAPDER_MODE == "task":
    from spiders.main_spider import MainSpider

    if __name__ == "__main__":
        MainSpider(task_table=f"{settings.PROJECT_NAME}.task").start()

else:
    raise ValueError(f"未知 FEAPDER_MODE: {settings.FEAPDER_MODE}")
