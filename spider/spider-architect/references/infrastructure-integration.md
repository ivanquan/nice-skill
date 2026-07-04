# 基础设施集成（数据库工具）

Phase 3 架构设计与 Phase 5 脚手架必须基于工作区 `数据库工具/` 下的三个工具类落地。

## 工具文件来源

生成项目时，将以下文件复制到 `{project}/utils/db/`，并**替换 settings 导入**：

| 源文件 | 目标 | 原 import | 替换为 |
|---|---|---|---|
| `数据库工具/redis_tool.py` | `utils/db/redis_tool.py` | `from TaskCenter.app.core.config import settings` | `import config.settings as settings` |
| `数据库工具/mysql_tool.py` | `utils/db/mysql_tool.py` | 同上 | 同上 |
| `数据库工具/mongo_tool.py` | `utils/db/mongo_tool.py` | 同上 | 同上 |

`config/settings.py` 必须提供工具类所需的全部字段（见 scaffold `config/settings.py` 模板）。

## RedisDB — 账号池（Hash + Set）

### Key 设计

| Key | 类型 | 用途 |
|---|---|---|
| `{PROJECT}:accounts:active` | Set | 可用账号 ID 集合，`sget` 随机取 |
| `{PROJECT}:accounts:detail` | Hash | `account_id` → JSON（cookie、ua、status、meta） |
| `{PROJECT}:accounts:banned` | Set | 失效/封禁账号，便于审计 |

### 核心 API（redis_tool.py）

```python
from utils.db.redis_tool import RedisDB

redis = RedisDB()  # 或 RedisDB(ip_ports=..., db=..., user_pass=...)

# 注册账号
redis.sadd(f"{project}:accounts:active", account_id)
redis.hset(f"{project}:accounts:detail", account_id, json.dumps(payload))

# 随机取账号（不弹出）
ids = redis.sget(f"{project}:accounts:active", count=1, is_pop=False)
detail = redis.hget(f"{project}:accounts:detail", ids[0])

# 失效回收
redis.srem(f"{project}:accounts:active", account_id)
redis.sadd(f"{project}:accounts:banned", account_id)
redis.hset(f"{project}:accounts:detail", account_id, json.dumps({**payload, "status": "banned"}))
```

参考：`redis_tool.py` 中 `sadd` / `sget` / `hset` / `hget` / `hgetall` / `srem` / `hdel`。

## RedisDB — 代理池（Set）

### Key 设计

| Key | 类型 | 用途 |
|---|---|---|
| `{PROJECT}:proxies:active` | Set | 可用代理 URL |
| `{PROJECT}:proxies:dead` | Set | 失效代理（冷却后可回迁） |

### 流程

1. `sget(active, count=1, is_pop=False)` 取代理
2. 请求失败 → `srem(active)` + `sadd(dead)`
3. 定时任务或启动时从 SmartProxy/ScraperAPI 拉取写入 `sadd(active)`

### 第三方代理

| 提供商 | 配置项 | 注入方式 |
|---|---|---|
| SmartProxy | `SMARTPROXY_GATEWAY_URL` | 固定网关或 API 拉取列表写入 Redis Set |
| ScraperAPI | `SCRAPERAPI_KEY` | `http://scraperapi:KEY@proxy-server.scraperapi.com:8001` |
| 自建池 | `PROXY_POOL_API` | HTTP 拉取 → `sadd(active)` |

## MysqlDB — 结构化存储

### 核心 API（mysql_tool.py）

```python
from utils.db.mysql_tool import MysqlDB

mysql = MysqlDB()  # PooledDB 连接池

# 单条插入（推荐）
mysql.add_smart(table="crawl_items", data={"url": "...", "title": "...", "created_at": "..."})

# 批量
mysql.add_batch_smart(table="crawl_items", datas=[{...}, {...}])

# 更新
mysql.update_smart(table="crawl_items", data={"status": 1}, condition='id=123')
```

Pipeline 中结构化字段（解析后的 Item dict）走 `add_smart`。

## MongoDB — 非结构化 / 原始响应

### 核心 API（mongo_tool.py）

```python
from utils.db.mongo_tool import MongoDB

mongo = MongoDB()
mongo.add(coll_name="crawl_raw", data={
    "url": request.url,
    "status_code": 200,
    "headers": dict(response.headers),
    "body": response.text,  # 或截断/压缩
    "spider": "main",
})
```

原始 HTML/JSON、调试日志、失败快照走 MongoDB。

## Phase 3 架构图中的基础设施层

```
Feapder Spider
    → Middleware (proxy_middleware ← RedisDB proxies:active)
    → account_pool ← RedisDB accounts Hash+Set
    → Parser → Item
    → mysql_pipeline (add_smart)  → MySQL
    → mongo_pipeline (add)        → MongoDB
```

## SKILL HOOK 与存储分工

| 数据类型 | 存储 | 代码位置 |
|---|---|---|
| 解析后结构化字段 | MySQL | `pipelines/mysql_pipeline.py` |
| 原始响应/日志/调试包 | MongoDB | `pipelines/mongo_pipeline.py` |
| 账号/Cookie 态 | Redis Hash+Set | `utils/account_pool.py` |
| 代理 | Redis Set | `middlewares/proxy_middleware.py` |
| 动态签名 | 不存库，运行时生成 | `utils/sign_helper.py` → 逆向 Skill |

## 依赖

```
feapder>=1.8.0
redis>=4.0.0
redis-py-cluster
pymysql
DBUtils
pymongo
requests
```
