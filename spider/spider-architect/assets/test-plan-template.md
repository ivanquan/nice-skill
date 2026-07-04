# 测试用例模板（Phase 6C）

> 复制到 `{project}/docs/test-plan.md` 并按项目填写。

---

## T1 冒烟测试

### T1.1 依赖与配置

- **目的**：确认 Python 包与 `.env` 可读
- **步骤**：
  1. `pip install -r requirements.txt`
  2. `python -c "from config import settings; print(settings.PROJECT_NAME)"`
- **预期**：无 ImportError，打印项目名

### T1.2 Redis

- **目的**：任务队列可用
- **命令**：`redis-cli -h {REDIS_HOST} ping`
- **预期**：`PONG`

### T1.3 API 健康检查（若有 FastAPI）

- **请求**：`GET /api/health`
- **预期**：`status: ok`，队列 pending 为数字

### T1.4 单条任务入队

- **请求**：`POST /api/tasks/enqueue`（单 keyword 或单 asin，`max_page=1`）
- **预期**：`queued >= 1`

---

## T2 功能测试

### T2.1 关键字搜索（每站点 1 条）

| platform | keyword | max_page | 检查项 |
|----------|---------|----------|--------|
| US | {sample} | 1 | MySQL 有 rank/asin/title；Mongo 有 HTML |

### T2.2 ASIN 详情（每站点 1 条）

| platform | asin | 检查项 |
|----------|------|--------|
| US | {sample} | title/price/rating 非空 |

### T2.3 触发爬虫并落库

- **步骤**：`POST /api/tasks/trigger` 或 `python main.py`
- **预期**：Redis 请求状态 `success`；MySQL/Mongo 有新记录

---

## T3 异常与容错

### T3.1 无效 ASIN

- **入队**：asin=`INVALID000`
- **预期**：重试后 `dead` 或达到最大重试；不污染 MySQL 脏数据

### T3.2 挑战页 / 验证码 HTML

- **方式**：用本地样本或触发风控
- **预期**：不入库结构化数据；任务进 retry 队列

### T3.3 代理/Cookie 失败

- **方式**：临时错误代理或错误 code
- **预期**：日志有 warning；retry 队列有任务

---

## T4 小规模压测（可选）

- **规模**：{N} keyword + {M} asin，线程 {SPIDER_THREAD_COUNT}
- **指标**：成功率、403/503 率、队列积压、平均耗时
- **预期**：成功率 > {X}%（用户自定）

---

## 测试执行记录

| 日期 | 用例 | 结果 | 备注 |
|------|------|------|------|
| | T1.1 | ☐ | |
