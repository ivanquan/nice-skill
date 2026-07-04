# {站点名} 企业级爬虫架构方案

> 生成工具：spider-architect | 版本：V1.2
> 状态：Phase 0–4 文档 / Phase 5 落地后更新为「已实现」

---

## 1. 目标概述

| 项 | 内容 |
|---|---|
| 目标网站 | |
| 数据类型 | |
| 数据用途 | 用户要求（最高准则） |
| Feapder 模式 | AirSpider / BatchSpider / TaskSpider |
| 模式决策理由 | Phase 0 诊断结论 |
| CHECKPOINT-0 确认 | 是 / 否 / 待确认 |

### Phase 0 诊断摘要

| 维度 | 用户回答 | 影响 |
|---|---|---|
| 规模与频次 | | |
| 并发与分布式 | | |
| 断点续传 | | |
| 调度复杂度 | | |

## 2. 反爬分析

| 项 | 内容 |
|---|---|
| 反爬等级 | L? |
| 关键机制 | |
| 证据来源 | |

## 3. 基础设施配置（Phase 0.5）

> CHECKPOINT-0.5 确认：是 / 否 / 待确认

### 3.1 代理

| 项 | 内容 |
|---|---|
| 是否启用 | |
| 提供商/方案 | redis 池 / SmartProxy / ScraperAPI / 其他 |
| API 文档 | （用户提供的链接） |
| Key 配置位置 | config/settings.py（占位） |
| 代理类型 | 住宅 / 数据中心 |
| 待补充材料 | |

### 3.2 打码 / 验证码

| 项 | 内容 |
|---|---|
| 是否启用 | |
| 验证码类型 | 滑块 / 图片 / AWS WAF / … |
| 打码平台 | 2Captcha / CapSolver / … |
| API 文档 | （用户提供的链接） |
| Key 配置位置 | config/settings.py（占位） |
| 待补充材料 | |

### 3.3 账号池

| 项 | 内容 |
|---|---|
| 是否启用 | |
| Cookie 来源 | 手动 / 登录 / Playwright |
| 待补充材料 | |

### 3.4 存储

| 组件 | 地址 | 库/表/集合 |
|---|---|---|
| Redis | | |
| MySQL | | |
| MongoDB | | |

### 3.5 调度与监控

| 项 | 内容 |
|---|---|
| 定时策略 | |
| 监控告警 | |

## 4. 抓取策略

| 项 | 内容 |
|---|---|
| 推荐策略 | 协议逆向 / Feapder 纯接口 / 混合 |
| 决策理由 | |
| 备选方案 | |

## 5. 合规与风控标注

> V1.2：标注风险，不拒绝方案；决策方为用户。

| 风险项 | 等级 | 说明 |
|---|---|---|
| ToS | | |
| robots.txt | | |
| 隐私/敏感数据 | | |

## 6. 项目架构

> CHECKPOINT-3 确认：是 / 否 / 待确认

### 6.1 目录结构

```text
（按 enterprise-modules.md + feapder_mode 填充）
```

### 6.2 基础设施集成

| 组件 | 工具类 | Key / 表 |
|---|---|---|
| 账号池 | RedisDB Hash+Set | `{prefix}:accounts:active/detail/banned` |
| 代理池 | RedisDB Set | `{prefix}:proxies:active/dead` |
| 结构化存储 | MysqlDB.add_smart | `{MYSQL_TABLE}` |
| 原始数据 | MongoDB.add | `{MONGO_RAW_COLL}` |

### 6.3 架构图

```
（Mermaid 或 ASCII）
```

## 7. 核心模块清单

| 模块 | 职责 | 脚手架文件 |
|---|---|---|
| Main Spider | | spiders/main_spider.py |
| Account Pool | | utils/account_pool.py |
| Proxy Middleware | | middlewares/proxy_middleware.py |
| Captcha Middleware | | middlewares/captcha_middleware.py（若启用） |
| MySQL Pipeline | add_smart | pipelines/mysql_pipeline.py |
| Mongo Pipeline | 原始响应 | pipelines/mongo_pipeline.py |

## 8. 风险点与缓解

| 风险 | 等级 | 类别 | 缓解措施 |
|---|---|---|---|

## 9. 脚手架清单（Phase 5 落地后勾选）

| 文件 | 状态 |
|---|---|
| config/settings.py | ☐ |
| utils/db/* | ☐ |
| utils/account_pool.py | ☐ |
| middlewares/proxy_middleware.py | ☐ |
| pipelines/mysql_pipeline.py | ☐ |
| pipelines/mongo_pipeline.py | ☐ |
| spiders/main_spider.py | ☐ |
| main.py | ☐ |

## 10. Skill 转交表

| 待实现项 | 代码位置 | 转交 Skill | 优先级 |
|---|---|---|---|
| 动态签名 | utils/sign_helper.py | dy-ab-pure / web-protocol-recovery | |
| Cookie/登录态 | utils/account_pool.py | web-protocol-recovery | |
| 打码集成 | middlewares/captcha_middleware.py | captcha-slide-reverse | |
| Node 补环境 | sign_helper | env-patch | |
| 瑞数 | account_pool | rs-reverse | |
| 验证码 | main_spider | captcha-slide-reverse | |

---

**说明**：Phase 0–4 为方案文档；**仅用户确认「开始落地脚手架」后**执行 Phase 5。

## 11. 落地后状态（Phase 6，V1.3）

> 脚手架生成后默认：**🟡 待配置**，非可运行态。详见 `docs/post-scaffold-status.md`。

| 阶段 | 状态 | CHECKPOINT |
|------|------|------------|
| 6A 待配置 | ☐ | CHECKPOINT-6A |
| 6B 待完善 | ☐ | CHECKPOINT-6B |
| 6C 待测试 | ☐ | CHECKPOINT-6C |

测试计划：`docs/test-plan.md`
