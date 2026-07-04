# Feapder 框架选型指南

V1.1 锁定 Feapder 生态（AirSpider / BatchSpider / TaskSpider + Playwright 混合）。

## Phase 0 模式决策映射

### 诊断问题清单

Phase 0 必须向用户确认（缺项则追问）：

1. **数据规模与频次**：单次抓取量级？是否每天持续增量？日增量上限？
2. **并发与分布式**：单机还是多机？是否需要水平扩展？
3. **容错与断点续传**：进程崩溃后是否从断点继续？能否接受重跑？
4. **任务调度复杂度**：是否 Cron 定时？任务间是否有依赖？是否需要动态下发子任务？

### 决策映射表

| 用户回答特征 | 推荐模式 | 理由 |
|---|---|---|
| 单次 / <10万 / 快速验证 / 无 Redis | **AirSpider** | 轻量、零依赖、内存去重 |
| 海量 / 分布式 / 断点续传 / 持久去重 | **BatchSpider** | Redis 队列 + 批次管理 + 断点 |
| 定时增量 / 任务依赖 / 动态下发 / Cron | **TaskSpider** | 内置任务调度与周期管理 |
| 多特征并存 | 取最高需求模式，次要在架构文档标注 | 例如：海量+定时 → BatchSpider + 外部 Cron |

### 决策树（ASCII）

```
数据规模？
├── 单次/小规模 ── 调度复杂？── 否 → AirSpider
│                          └── 是 → TaskSpider
└── 海量/持续 ── 需断点/分布式？── 是 → BatchSpider
                              └── 否 → TaskSpider 或 AirSpider+Redis
```

## Feapder 核心形态

| 形态 | 适用场景 | 依赖 | 去重 |
|---|---|---|---|
| **AirSpider** | 验证、小规模、单机 | 无 Redis | 内存 |
| **BatchSpider** | 大批量、断点续爬、分布式 | Redis | Redis 持久 |
| **TaskSpider** | 定时、周期、任务驱动 | Redis（通常） | Redis |

## 抓取层模式（与 Phase 2 配合）

### 纯接口模式

```
Feapder {Air|Batch|Task}Spider
  ├── Request + sign/cookie（Middleware 注入）
  ├── Parser
  └── Pipeline
```

### Feapder + Playwright 混合

```
Playwright 取态 → Redis/账号池 → Spider Middleware 消费态
```

L4+ 时在脚手架中生成 `services/playwright_state.py`。

## 组件映射

| 企业需求 | Feapder 组件 | 脚手架文件 |
|---|---|---|
| 模式配置 | settings | `config/settings.py` |
| 请求/解析 | Spider | `spiders/main_spider.py` |
| 代理轮换 | Middleware | `middlewares/proxy_middleware.py` |
| 账号/Cookie | 外部服务 | `utils/account_pool.py` |
| 签名 | 外部 helper | `utils/sign_helper.py`（L3+） |
| 数据清洗 | Pipeline | `pipelines/`（按需扩展） |

## 架构图模板

```
Phase 0 选型: {AirSpider|BatchSpider|TaskSpider}
        │
        ▼
┌───────────────┐     ┌───────────────┐
│ Account Pool   │     │  Proxy Pool    │
└───────┬───────┘     └───────┬───────┘
        └──────────┬───────────┘
                   ▼
            ┌─────────────┐
            │ Feapder      │
            │ Main Spider  │
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │  Pipeline    │ → Storage
            └─────────────┘
```
