# 脚手架生成指南（Phase 5 ONLY）

> **V1.2 门禁**：本指南仅在用户通过 CHECKPOINT-0、0.5、3 并明确回复「开始落地脚手架」后执行。Phase 0–4 禁止执行本文件中的任何文件创建操作。

## 前置确认清单

执行前自检：

```
[ ] CHECKPOINT-0：feapder_mode 已确认
[ ] CHECKPOINT-0.5：代理/打码/DB/账号配置已确认（或标注待补充）
[ ] CHECKPOINT-3：架构摘要已确认
[ ] 用户原话含「开始落地」「生成代码」「确认架构」等明确授权
```

缺任一项 → **停止**，回到对应 Phase 补问或等确认。

## 生成流程

1. 确认 Phase 0 `feapder_mode`、Phase 0.5 基础设施摘要、`{project_name}`、工作区路径。
2. 在用户指定工作区创建 `{project_name}/`。
3. **复制数据库工具**（见 [infrastructure-integration.md](infrastructure-integration.md)）。
4. 从 [assets/scaffold/](../assets/scaffold/) 复制模板并替换占位符。
5. **`config/settings.py` 按 Phase 0.5 问卷结果填写**（API Key 用 `""` 或 `YOUR_XXX_KEY` 占位）。
6. 按模式复制 spider 模板 → `spiders/main_spider.py`。
7. 写入 `docs/architecture-report.md`（汇总 Phase 0–4）。
8. **V1.3** 生成落地后文档：
   - `docs/post-scaffold-status.md` ← [post-scaffold-status-template.md](../assets/post-scaffold-status-template.md)
   - `docs/test-plan.md` ← [test-plan-template.md](../assets/test-plan-template.md)
9. 交付：架构报告 + 代码 + Skill 转交表。
10. **必须进入 Phase 6A**（见 [post-scaffold-guide.md](post-scaffold-guide.md)），告知项目为「待配置」状态。

## 目录结构

```text
{project_name}/
├── config/
│   └── settings.py                 # 按 Phase 0.5 问卷填充
├── docs/
│   └── architecture-report.md      # Phase 0–4 汇总
├── utils/
│   ├── account_pool.py
│   ├── sign_helper.py              # L3+
│   └── db/
│       ├── redis_tool.py           ← 从 数据库工具/ 复制
│       ├── mysql_tool.py
│       ├── mongo_tool.py
│       ├── redis_client.py
│       ├── mysql_client.py
│       └── mongo_client.py
├── middlewares/
│   ├── proxy_middleware.py         # 按代理方案选型
│   └── captcha_middleware.py       # 若 Phase 0.5 确认打码
├── pipelines/
│   ├── mysql_pipeline.py
│   └── mongo_pipeline.py
├── spiders/
│   └── main_spider.py
├── services/
│   ├── playwright_state.py         # L4+ 且用户确认
│   └── scheduler_seed.py           # 若有时序调度
├── crawler_cache/
├── main.py
└── requirements.txt
```

## 10 个核心文件清单

| 文件 | 模板源 |
|---|---|
| `config/settings.py` | `assets/scaffold/config/settings.py` + Phase 0.5 配置 |
| `spiders/main_spider.py` | `main_spider_{air\|batch\|task}.py` |
| `middlewares/proxy_middleware.py` | `assets/scaffold/middlewares/` |
| `utils/account_pool.py` | `assets/scaffold/utils/` |
| `pipelines/mysql_pipeline.py` | `assets/scaffold/pipelines/` |
| `pipelines/mongo_pipeline.py` | `assets/scaffold/pipelines/` |
| `utils/db/*_client.py` + 三个 tool 复制 | infrastructure-integration.md |
| `utils/sign_helper.py` | L3+ 从 scaffold 复制 |
| `main.py` | `assets/scaffold/main.py` |
| `requirements.txt` | `assets/scaffold/requirements.txt` |

## settings.py 填充规则（来自 Phase 0.5）

| 配置项 | 来源 |
|--------|------|
| `PROXY_ENABLE` / `PROXY_PROVIDER` | 代理问卷 |
| `SMARTPROXY_GATEWAY_URL` / `SCRAPERAPI_KEY` / `PROXY_POOL_API` | 用户提供，占位符 |
| `CAPTCHA_ENABLE` / `CAPTCHA_PROVIDER` / `CAPTCHA_API_KEY` | 打码问卷 |
| `REDIS_*` / `MYSQL_*` / `Mongo_*` | 存储问卷 |
| `ACCOUNT_POOL_ENABLE` | 账号问卷 |
| `PLAYWRIGHT_ENABLE` | 浏览器混合问卷 |
| `SPIDER_THREAD_COUNT` / `REQUEST_DELAY` | Phase 0 规模与并发 |

**禁止**：在 skill 或 scaffold 中硬编码用户提供的真实 API Key。

## 数据库工具复制（强制）

```text
数据库工具/redis_tool.py  → {project}/utils/db/redis_tool.py
数据库工具/mysql_tool.py  → {project}/utils/db/mysql_tool.py
数据库工具/mongo_tool.py  → {project}/utils/db/mongo_tool.py
```

```python
# 替换
from TaskCenter.app.core.config import settings
# 为
import config.settings as settings
```

## Spider 模板选择

| feapder_mode | 模板 | 基类 |
|---|---|---|
| `air` | `main_spider_air.py` | `feapder.AirSpider` |
| `batch` | `main_spider_batch.py` | `feapder.BatchSpider` |
| `task` | `main_spider_task.py` | `feapder.TaskSpider` |

## Skill Hook 清单

| Hook | 位置 | 转交 |
|---|---|---|
| sign_helper | `utils/sign_helper.py` | dy-ab-pure / web-protocol-recovery |
| mysql_storage | `pipelines/mysql_pipeline.py` | 结构化 Item |
| mongo_storage | `pipelines/mongo_pipeline.py` | 原始 `_raw` |
| account_login | `utils/account_pool.py` | web-protocol-recovery / rs-reverse |
| playwright_state | `services/playwright_state.py` | web-protocol-recovery |
| captcha | `middlewares/captcha_middleware.py` | captcha-slide-reverse |
| env-patch | spider 注释 | env-patch |

## 启动

```bash
pip install -r requirements.txt
# 用户填写 config/settings.py 中的 Key 与连接串
python main.py
```

签名/Cookie/打码需逆向 Skill 或用户 API 配置完成后方能完整跑通。
