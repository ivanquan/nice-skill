"""MySQL Pipeline — 结构化数据存储（mysql_tool.add_smart）。"""

from config import settings

# --- SKILL HOOK: mysql_storage ---
# 结构化 Item 字段入库；表结构需与 MYSQL_TABLE 对齐
# --- END SKILL HOOK ---


class MysqlPipeline:
    def __init__(self):
        self.enabled = settings.MYSQL_PIPELINE_ENABLE
        self.table = settings.MYSQL_TABLE
        self._mysql = None

    def open_spider(self, spider):
        if not self.enabled:
            return
        from utils.db.mysql_client import get_mysql

        self._mysql = get_mysql()

    def process_item(self, item, spider):
        if not self.enabled or not self._mysql:
            return item

        data = dict(item) if not isinstance(item, dict) else item
        # 仅写入结构化字段；原始 body 走 mongo_pipeline
        structured = {k: v for k, v in data.items() if k != "_raw"}
        if structured:
            self._mysql.add_smart(table=self.table, data=structured)
        return item

    def close_spider(self, spider):
        self._mysql = None
