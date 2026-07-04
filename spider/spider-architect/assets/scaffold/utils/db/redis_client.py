"""RedisDB 客户端 — 封装 数据库工具/redis_tool.py。"""

from config import settings

# 生成项目时：复制 数据库工具/redis_tool.py → utils/db/redis_tool.py
# 并将 from TaskCenter.app.core.config import settings 改为 import config.settings as settings

try:
    from utils.db.redis_tool import RedisDB
except ImportError as e:
    raise ImportError(
        "请复制 数据库工具/redis_tool.py 到 utils/db/ 并修正 settings 导入"
    ) from e


def get_redis() -> RedisDB:
    return RedisDB(
        ip_ports=f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        db=settings.REDIS_DB,
        user_pass=settings.REDIS_PASSWORD or None,
    )
