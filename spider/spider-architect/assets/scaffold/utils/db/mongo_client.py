"""MongoDB 客户端 — 封装 数据库工具/mongo_tool.py。"""

from config import settings

try:
    from utils.db.mongo_tool import MongoDB
except ImportError as e:
    raise ImportError(
        "请复制 数据库工具/mongo_tool.py 到 utils/db/ 并修正 settings 导入"
    ) from e


def get_mongo() -> MongoDB:
    return MongoDB(
        ip=settings.Mongo_IP,
        db=settings.MONGODB_DB,
        user_name=settings.Mongo_username or None,
        user_pass=settings.Mongo_password or None,
    )
