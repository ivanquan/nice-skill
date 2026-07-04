# 企业级爬虫模块设计规范

## 标准项目结构（Feapder）

Phase 5 脚手架以 [assets/scaffold/](../assets/scaffold/) 为模板，按 `feapder_mode` 选型。

```text
project/
├── config/
│   └── settings.py          # FEAPDER_MODE: air|batch|task
├── spiders/                 # Feapder Spider 定义
│   ├── __init__.py
│   └── main_spider.py       # 由 air/batch/task 模板生成
├── items/                   # 数据结构定义
│   └── {target}_item.py
├── pipelines/               # 清洗、去重、写入
│   ├── clean_pipeline.py
│   └── storage_pipeline.py
├── middlewares/             # Cookie、代理、重试、sign 注入
│   ├── cookie_middleware.py
│   ├── proxy_middleware.py
│   └── sign_middleware.py
├── services/                # 外部服务封装
│   ├── account_pool.py      # 账号池
│   ├── proxy_pool.py        # 代理池
│   ├── playwright_state.py  # Playwright 取态（L4+）
│   └── sign_helper.py       # 签名 helper（协议逆向产出）
├── utils/                   # 工具函数
├── config/                  # 环境配置（不含密钥明文）
│   ├── settings.py
│   └── logging.conf
├── tests/                   # 单元/集成测试
├── docs/                    # 架构文档、接口说明
└── main.py                  # 启动入口
```

## 基础设施模块（Phase 3 必设计）

读取 [infrastructure-integration.md](infrastructure-integration.md)。

| 模块 | 工具 | Redis Key / 表 |
|---|---|---|
| Account Pool | `RedisDB` hset+sadd | `{prefix}:accounts:active/detail/banned` |
| Proxy Pool | `RedisDB` sadd+srem | `{prefix}:proxies:active/dead` |
| 结构化存储 | `MysqlDB.add_smart` | `settings.MYSQL_TABLE` |
| 原始数据 | `MongoDB.add` | `settings.MONGO_RAW_COLL` |

脚手架文件映射见 [scaffold-guide.md](scaffold-guide.md)。

## 核心模块清单

| 模块 | 职责 | 必选 | Feapder 映射 |
|---|---|---|---|
| **Scheduler** | 任务调度、增量策略、周期触发 | 生产必选 | TaskSpider / 外部 Cron |
| **Spider** | 请求生成、翻页、种子管理 | 必选 | `spiders/` |
| **Parser** | 响应解析、字段提取 | 必选 | Spider 内 `parse` |
| **Middleware** | Cookie/代理/sign/重试 | L2+ | `middlewares/` |
| **Pipeline** | 清洗、去重、落库 | 必选 | `pipelines/` |
| **Account Pool** | 账号注册、登录、轮换、封禁检测 | L3+ | `services/account_pool.py` |
| **Proxy Pool** | 代理获取、健康检查、轮换 | L2+ | `services/proxy_pool.py` |
| **Sign Helper** | 离线签名生成 | L3 协议逆向 | `services/sign_helper.py` |
| **Playwright State** | 浏览器取态、Cookie 导出 | L4+ 混合 | `services/playwright_state.py` |
| **Storage** | DB/ES/Kafka/OSS | 必选 | Pipeline 后端 |
| **Monitor** | 成功率、延迟、封禁率、告警 | 生产必选 | 独立服务或 Pipeline 打点 |
| **Config** | 环境隔离、限流参数 | 必选 | `config/` |

## 数据流

```
Seed URL / 账号任务
    → Scheduler 分发
    → Spider 构造 Request
    → Middleware 注入 Cookie/Proxy/Sign
    → HTTP 请求
    → Parser 提取 Item
    → Pipeline 清洗 → 去重 → 存储
    → Monitor 采集指标
```

混合模式附加流：

```
Account Pool 分配账号
    → Playwright State 登录/取态
    → 态写入 Redis/账号池
    → Spider Middleware 读取态
    → (失效) → 回调 Playwright 刷新
```

## 模块设计原则

1. **Sign 与 Spider 解耦**：sign helper 由 `web-protocol-recovery` / `dy-ab-pure` 产出，Spider 只调用接口。
2. **态与抓分解耦**：Playwright 只管取态，Feapder 只管协议抓。
3. **账号与请求绑定**：Middleware 层保证同一账号的请求序列一致性。
4. **失败可观测**：每次 403/sign 失效/验证码触发必须打点，便于调策略。
5. **配置外置**：QPS、代理比例、重试次数不进代码硬编码。

## 规模 × Feapder 模式（Phase 0 映射）

| 规模 / 特征 | Feapder 模式 | 架构要点 |
|---|---|---|
| 单次 / <10万 / 验证 | **AirSpider** | 单机 + 内存去重 |
| 海量 / 断点续传 / 分布式 | **BatchSpider** | Redis + 持久去重 + 代理池 |
| 定时 / 任务依赖 / 动态下发 | **TaskSpider** | Redis + 任务表 + Cron |

## 与逆向 Skill 的衔接

| 模块 | 逆向 Skill 产出物 |
|---|---|
| `sign_helper.py` | `web-protocol-recovery` / `dy-ab-pure` |
| `playwright_state.py` | 混合模式设计，`camoufox-js-reverse` 辅助定位 |
| Cookie /bootstrap 逻辑 | `web-protocol-recovery` / `rs-reverse` |
| 验证码处理 | `captcha-slide-reverse` |

架构文档中必须为每个 L3+ 模块标注「产出 Skill」和「待逆向项」。
