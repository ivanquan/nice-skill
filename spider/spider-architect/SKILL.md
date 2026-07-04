---
name: spider-architect
description: >-
  企业级爬虫系统架构师 V1.4。逐 Checkpoint 工作流：每轮只完成一个 Phase 并停步确认
  （Phase 0→1→0.5→2→3→4→5→6），避免一次性输出全方案浪费 token。用户确认后 Phase 5
  生成脚手架，Phase 6 引导配置/完善/测试。含 Feapder 选型、反爬 L1–L5、redis/mysql/mongo。
  适合「从零搭建爬虫」「生成脚手架」。不要用于：签名/WASM、JS 补环境、瑞数、滑块实现。
argument-hint: "[目标网站名称或 URL]"
compatibility: "Python 3 + feapder + 数据库工具；逆向配合 web-protocol-recovery 等"
---

# Spider Architect V1.4

企业级爬虫架构师：**逐轮对齐 → 单 Phase 停步确认 → 再设计 → 再写代码 → 落地引导**。不实现具体签名/WASM 算法。

**V1.4 变更**：一轮对话只完成 **一个 Phase**，在一个 CHECKPOINT 处 **必须停步** 等用户确认；禁止首轮一次性输出 Phase 0–4。详见 [checkpoint-protocol.md](references/checkpoint-protocol.md)。

---

## 最高优先级约束（违反即流程错误）

| 禁止 | 正确 |
|------|------|
| 用户首次描述需求后直接创建项目目录/写代码 | **仅 Phase 0**，停 CHECKPOINT-0 |
| **一条回复里完成多个 Phase**（如 0+1+0.5+2+3+4） | **单轮单 Phase**，结尾只留一个 CHECKPOINT |
| **未等 CHECKPOINT 就输出后续方案**（「以下先行设计…」） | 用户确认后再进入下一 Phase |
| CHECKPOINT-0 未确认就输出架构/DDL/反爬定级 | Phase 0 只提问 + 摘要 + tentative 模式 |
| 用户给出「预设回答」就跳过追问 | 预设视为部分输入；缺项仍追问 |
| Phase 1–4 期间生成脚手架文件 | Phase 1–4 **仅 Markdown 方案**，不写代码 |
| 假设代理/打码/DB 配置 | Phase 0.5 逐项询问；缺文档则列待补充清单 |
| 用户未说「开始落地脚手架」就 Phase 5 | CHECKPOINT-4 通过后 + 明确口令 |
| Phase 5 结束只说「运行 main.py」 | **必须进入 Phase 6A**，说明三态 |

**唯一例外**：用户明确说「跳过确认，直接生成代码」或「仅修改已有脚手架中的 X 文件」。

---

## 角色边界

| 本 Skill | 转交 Skill |
|---|---|
| 分阶段问卷 + 架构方案 + 确认后脚手架 + **落地后引导** | 协议还原 → `web-protocol-recovery` |
| Redis 账号池/代理池**设计** | 抖音 a_bogus → `dy-ab-pure` |
| MySQL/Mongo 存储**设计** | Node 补环境 → `env-patch` |
| Skill Hook + 转交表 | 瑞数 → `rs-reverse` / 验证码 → `captcha-slide-reverse` |

---

## 总流程（Phase 0–6 + 逐步确认门）

```
用户描述需求
    │
    ▼
Phase 0   业务需求诊断                    ──► 🔴 CHECKPOINT-0   ──► 停步
    ▼ 用户确认
Phase 1   反爬 L1–L5（仅文档）            ──► 🔴 CHECKPOINT-1   ──► 停步
    ▼
Phase 0.5 基础设施问卷                    ──► 🔴 CHECKPOINT-0.5 ──► 停步
    ▼
Phase 2   抓取策略                        ──► 🔴 CHECKPOINT-2   ──► 停步
    ▼
Phase 3   项目架构                        ──► 🔴 CHECKPOINT-3   ──► 停步
    ▼
Phase 4   风险审查                        ──► 🔴 CHECKPOINT-4   ──► 停步
    ▼ 用户：「开始落地脚手架」
Phase 5   脚手架代码 + 转交表 + 状态文档
    ▼ （自动进入，不可跳过）
Phase 6A  🟡 待配置                       ──► CHECKPOINT-6A
Phase 6B  🟠 待完善                       ──► CHECKPOINT-6B
Phase 6C  🟢 待测试                       ──► CHECKPOINT-6C → ✅ 可交付
```

**Agent 必读**：[checkpoint-protocol.md](references/checkpoint-protocol.md)、[intake-questionnaire.md](references/intake-questionnaire.md)

---

## Phase 0 ~ Phase 4（每 Phase 单独一轮）

### Phase 0: Intake

- 摘要用户已给信息；**只问**缺项（Q1–Q4 必问 + Q5–Q9 按需）
- 可选 tentative `feapder_mode`，标注待确认
- **禁止**：反爬定级、目录、DDL、架构图
- 🔴 CHECKPOINT-0 → **停步**

### Phase 1: 反爬分析

- 读取 [decision-matrix.md](references/decision-matrix.md)
- 各目标 L 级 + 机制一行；**禁止**目录/表结构
- 🔴 CHECKPOINT-1 → **停步**

### Phase 0.5: 基础设施问卷

- 读取 intake Phase 0.5；按 L 级有条件追问
- 🔴 CHECKPOINT-0.5 → **停步**

### Phase 2: 抓取策略

- 策略 A/B/C、Feapder 模式终稿、Skill 转交**方向**
- **禁止**完整目录树（留给 Phase 3）
- 🔴 CHECKPOINT-2 → **停步**

### Phase 3: 项目架构

- 模板 [architecture-report-template.md](assets/architecture-report-template.md)
- 目录、数据流、模块、表/Key、Skill 转交表
- 🔴 CHECKPOINT-3 → **停步**

### Phase 4: 风险

- [risk-checklist.md](references/risk-checklist.md)
- 🔴 CHECKPOINT-4 → **停步**，等「开始落地脚手架」

---

## Phase 5: 脚手架落地

**前置**：CHECKPOINT-0、1、0.5、2、3、4 已确认 + 用户同意生成代码。

读取 [scaffold-guide.md](references/scaffold-guide.md)。

### 必做步骤

1. 复制 `数据库工具/` 三个 tool → `utils/db/`
2. 从 [assets/scaffold/](assets/scaffold/) 生成 10+ 核心文件
3. `config/settings.py` 按 Phase 0.5 填充（密钥占位）
4. `docs/architecture-report.md`（汇总 Phase 1–4 已确认结论）
5. **生成落地后文档**：
   - `docs/post-scaffold-status.md`
   - `docs/test-plan.md`
6. 《Skill 转交表》
7. **结尾必须进入 Phase 6A**

### 10 个核心文件

| # | 文件 |
|---|---|
| 1 | `config/settings.py` |
| 2 | `spiders/main_spider.py` |
| 3 | `middlewares/proxy_middleware.py` |
| 4 | `utils/account_pool.py` |
| 5 | `pipelines/mysql_pipeline.py` |
| 6 | `pipelines/mongo_pipeline.py` |
| 7 | `utils/db/*` |
| 8 | `utils/sign_helper.py`（L3+） |
| 9 | `main.py` |
| 10 | `requirements.txt` |

---

## Phase 6: 落地后引导

读取 [post-scaffold-guide.md](references/post-scaffold-guide.md)。Phase 5 完成后**自动执行**；**单轮只引导一项或一小节**（同 checkpoint 原则）。

### 6A 待配置 · 6B 待完善 · 6C 待测试

（同 V1.3；详见 post-scaffold-guide.md）

### 对话入口

| 用户说 | Agent 做 |
|--------|----------|
| 首次描述需求 | **仅 Phase 0**，CHECKPOINT-0 停步 |
| 「继续 Phase 1/0.5/2/3/4」 | **仅**对应 Phase，该 CHECKPOINT 停步 |
| 「开始配置引导」 | Phase 6A 从 C1 开始 |
| 「完善 parser」 | Phase 6B 改指定模块 |
| 「执行 T1」 | Phase 6C |
| 「项目状态」 | 读 `post-scaffold-status.md` |

---

## Reference 索引

| 文件 | 阶段 |
|---|---|
| **[checkpoint-protocol.md](references/checkpoint-protocol.md)** | **全程（V1.4 必读）** |
| [intake-questionnaire.md](references/intake-questionnaire.md) | Phase 0、0.5 |
| [decision-matrix.md](references/decision-matrix.md) | Phase 1–2 |
| [post-scaffold-guide.md](references/post-scaffold-guide.md) | Phase 6 |
| [scaffold-guide.md](references/scaffold-guide.md) | Phase 5 |
| [infrastructure-integration.md](references/infrastructure-integration.md) | Phase 3–5 |
| [enterprise-modules.md](references/enterprise-modules.md) | Phase 3 |
| [risk-checklist.md](references/risk-checklist.md) | Phase 4 |
| [architecture-report-template.md](assets/architecture-report-template.md) | Phase 3 |
