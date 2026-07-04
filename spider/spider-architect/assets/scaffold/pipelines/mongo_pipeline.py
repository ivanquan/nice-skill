"""MongoDB Pipeline — 非结构化/原始响应存储（mongo_tool.add）。"""

from config import settings

# --- SKILL HOOK: mongo_storage ---
# 原始 HTML/JSON、headers、调试快照存 MongoDB
# --- END SKILL HOOK ---


class MongoPipeline:
    def __init__(self):
        self.enabled = settings.MONGO_PIPELINE_ENABLE
        self.collection = settings.MONGO_RAW_COLL
        self._mongo = None

    def open_spider(self, spider):
        if not self.enabled:
            return
        from utils.db.mongo_client import get_mongo

        self._mongo = get_mongo()

    def process_item(self, item, spider):
        if not self.enabled or not self._mongo:
            return item

        data = dict(item) if not isinstance(item, dict) else item
        raw_doc = data.get("_raw")
        if raw_doc is None:
            # 无 _raw 时仍将全量 item 存一份便于调试
            raw_doc = {k: v for k, v in data.items()}

        self._mongo.add(
            coll_name=self.collection,
            data=raw_doc if isinstance(raw_doc, dict) else {"body": raw_doc},
            insert_ignore=True,
        )
        return item

    def close_spider(self, spider):
        self._mongo = None
