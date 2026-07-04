"""Feapder 项目配置 — 由 spider-architect 生成。"""

# --- 模式配置（Phase 0 决策）---
# air | batch | task
FEAPDER_MODE = "{FEAPDER_MODE}"

PROJECT_NAME = "{PROJECT_NAME}"
TARGET_DOMAIN = "{TARGET_DOMAIN}"

# --- Feapder Redis（batch/task）---
REDISDB_IP_PORTS = "127.0.0.1:6379"
REDISDB_USER_PASS = ""
REDISDB_DB = 0

# --- RedisDB 工具类（redis_tool.py 读取）---
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ""

# --- MySQL（mysql_tool.py / MysqlDB 连接池）---
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_DATABASE = "crawler"
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_TABLE = "crawl_items"  # add_smart 默认表名

# --- MongoDB（mongo_tool.py）---
Mongo_IP = "127.0.0.1"
MONGODB_DB = "crawler"
Mongo_username = ""
Mongo_password = ""
MONGO_RAW_COLL = "crawl_raw"  # 原始响应集合

# --- 并发与限速 ---
SPIDER_THREAD_COUNT = 8
SPIDER_MAX_RETRY_TIMES = 3
REQUEST_TIMEOUT = 30

# --- 代理池 ---
PROXY_ENABLE = False
# redis | smartproxy | scraperapi | api
PROXY_PROVIDER = "redis"
PROXY_POOL_API = ""  # 自建代理 API
SMARTPROXY_GATEWAY_URL = ""  # http://user:pass@gate.smartproxy.com:7000
SCRAPERAPI_KEY = ""

# Redis Key 前缀（账号池/代理池）
REDIS_KEY_PREFIX = "{PROJECT_NAME}"

# --- 账号池 ---
ACCOUNT_POOL_ENABLE = True

# --- 存储 Pipeline ---
MYSQL_PIPELINE_ENABLE = True
MONGO_PIPELINE_ENABLE = True

# --- Playwright 混合模式（L4+）---
PLAYWRIGHT_ENABLE = False
PLAYWRIGHT_STATE_REDIS_KEY = "crawler:playwright:state"
