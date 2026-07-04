"""MysqlDB 客户端 — 封装 数据库工具/mysql_tool.py。"""

from config import settings

try:
    from utils.db.mysql_tool import MysqlDB
except ImportError as e:
    raise ImportError(
        "请复制 数据库工具/mysql_tool.py 到 utils/db/ 并修正 settings 导入"
    ) from e


def get_mysql() -> MysqlDB:
    return MysqlDB(
        ip=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        db=settings.MYSQL_DATABASE,
        user_name=settings.MYSQL_USER,
        user_pass=settings.MYSQL_PASSWORD,
    )
