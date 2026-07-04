# Checkpoint 协议（V1.4）

**核心原则：一轮对话只完成一个 Phase，停在一个 CHECKPOINT，等用户确认后再继续。**

前期对齐颗粒度；架构与脚手架仅在 CHECKPOINT-0 / 0.5 / 2 / 3 / 4 全部通过后才开始 Phase 5。

---

## 为什么

| 问题 | 后果 |
|------|------|
| 首轮一次性输出 Phase 0–4 | 浪费 token；用户改 Q1–Q4 后后续方案作废 |
| 未等 CHECKPOINT 就写架构 | 反爬等级、基础设施未定，目录/表结构易返工 |
| 「基于当前信息先行设计」 | 违反确认门；给用户错误预期 |

---

## 铁律（违反即流程错误）

1. **单轮单 Phase**：每条 Agent 回复最多执行 **一个** Phase（Phase 6A/B/C 同理，一次只引导一项或一小节）。
2. **必须停步**：每个 Phase 结尾 **只有** 该 Phase 的 CHECKPOINT + 一句「请确认后再继续」；**禁止**在同一条回复里进入下一 Phase。
3. **禁止预演**：不得输出「以下 Phase X 先行设计」「若您确认则可继续」并附带后续 Phase 正文。
4. **禁止抢跑架构**：CHECKPOINT-0 未确认前，不得出现目录结构、MySQL 表 DDL、Redis Key、Mermaid 架构图。
5. **禁止抢跑反爬**：CHECKPOINT-0 未确认前，不得给出 L1–L5 定级（可在 Phase 0 用一句话说明「待 Phase 1 评估」）。
6. **用户改前面 → 作废后面**：用户在任何 CHECKPOINT 修改已确认项时，从 **被改 Phase 的下一 Phase** 重新执行，不沿用旧方案段落。

---

## Phase 顺序与停步点

```
用户描述需求
    │
    ▼
Phase 0   业务诊断（提问 + 摘要）          ──► 🔴 CHECKPOINT-0   ──► 停，等用户
    │ 用户：「继续 Phase 1」或确认摘要
    ▼
Phase 1   反爬 L1–L5（仅文档）             ──► 🔴 CHECKPOINT-1   ──► 停，等用户
    │
    ▼
Phase 0.5 基础设施问卷                     ──► 🔴 CHECKPOINT-0.5 ──► 停，等用户
    │
    ▼
Phase 2   抓取策略（A/B/C + 理由）         ──► 🔴 CHECKPOINT-2   ──► 停，等用户
    │
    ▼
Phase 3   项目架构（目录/数据流/模块）      ──► 🔴 CHECKPOINT-3   ──► 停，等用户
    │
    ▼
Phase 4   风险审查                         ──► 🔴 CHECKPOINT-4   ──► 停，等用户
    │
    ▼ 用户：「开始落地脚手架」
Phase 5   脚手架代码
    │
    ▼
Phase 6A/B/C（逐项，同单轮单步原则）
```

---

## 各 Phase 输出预算（控制 token）

| Phase | 允许输出 | 禁止输出 |
|-------|----------|----------|
| **0** | 已收输入摘要表；缺项问题列表；可选 ** tentative ** `feapder_mode`（标注待确认） | 反爬定级、架构、DDL、Skill 转交表 |
| **1** | 各目标 L 级表；关键机制一行；策略方向一句 | 目录结构、MySQL 表、基础设施细节 |
| **0.5** | 按 L 级有条件追问；配置摘要表；待补充材料清单 | 完整架构图、parser 设计 |
| **2** | 策略 A/B/C 选型表；Feapder 模式最终确认；Skill 转交 **方向**（不含实现） | 完整目录树、Redis Key 全集 |
| **3** | 目录结构、数据流、模块清单、表/Key 设计、转交表 | 风险长篇、脚手架代码 |
| **4** | 风险表（合规优先）；缓解措施一行 | 任何代码或文件创建 |
| **5+** | 按 scaffold-guide | — |

---

## 用户首轮给大量预设时（典型：多平台监控）

**正确 Phase 0 单轮回复结构：**

1. 一句话确认角色与当前阶段（「Phase 0 业务诊断」）
2. **已接收输入** 小表（平台、任务、已知基础设施）
3. **仍缺项** 列表（Q1–Q4 必问 + 按需 Q5–Q9）
4. 若信息足够可 ** tentative ** 推荐 `feapder_mode`，必须写「待您确认 CHECKPOINT-0」
5. **🔴 CHECKPOINT-0** + 「确认请回复 …；修改请直接说明」
6. **结束** — 无 Phase 1 及以后内容

---

## CHECKPOINT 确认话术

### CHECKPOINT-0

```markdown
## 🔴 CHECKPOINT-0
- 已确认 / 待确认：（业务边界、任务颗粒度、feapder_mode 建议）
- 缺项：（若仍有）

请确认以上摘要与模式建议。确认请回复「继续 Phase 1」；有修改请直接说明。
```

### CHECKPOINT-1

```markdown
## 🔴 CHECKPOINT-1
- 反爬等级摘要：（表格一行/平台）
- 策略方向：（一句话）

确认请回复「继续 Phase 0.5」；有异议请说明。
```

### CHECKPOINT-0.5

```markdown
## 🔴 CHECKPOINT-0.5
- 代理 / 打码 / 账号 / Redis / 存储：（各一行）
- 待补充材料：（列表）

确认请回复「继续 Phase 2」。
```

### CHECKPOINT-2

```markdown
## 🔴 CHECKPOINT-2
- 抓取策略：（A/B/C 表）
- Skill 转交方向：（列表，无实现细节）

确认请回复「继续 Phase 3」。
```

### CHECKPOINT-3

```markdown
## 🔴 CHECKPOINT-3
- 架构摘要：（目录 + 数据流 + 核心模块 3–5 行）

确认请回复「继续 Phase 4」；或「开始落地脚手架」若您希望跳过风险展开（仍建议先看 Phase 4）。
```

### CHECKPOINT-4

```markdown
## 🔴 CHECKPOINT-4
- 风险 Top3 + 合规标注

确认请回复「开始落地脚手架」后才会创建项目文件。
```

---

## 用户指令映射

| 用户说 | Agent 做 |
|--------|----------|
| 首次描述需求 | **仅 Phase 0**，停 CHECKPOINT-0 |
| 「继续 Phase 1」 | **仅 Phase 1**，停 CHECKPOINT-1 |
| 「继续 Phase 0.5」 | **仅 Phase 0.5**，停 CHECKPOINT-0.5 |
| 「继续 Phase 2」 | **仅 Phase 2**，停 CHECKPOINT-2 |
| 「继续 Phase 3」 | **仅 Phase 3**，停 CHECKPOINT-3 |
| 「继续 Phase 4」 | **仅 Phase 4**，停 CHECKPOINT-4 |
| 「开始落地脚手架」 | Phase 5（需 0/0.5/2/3/4 已确认；缺项则先补确认） |
| 「一次性全给方案」 | 仍建议分 checkpoint；若用户坚持，最多合并 **相邻两 Phase**，且须声明返工风险 |
| 在某 CHECKPOINT 修改前面答案 | 从该 Phase **重跑** 后续，不引用旧架构段落 |

---

## 例外

| 情况 | 行为 |
|------|------|
| 用户说「跳过确认，直接生成代码」 | 可跳至 Phase 5，须在回复开头列出假设清单 |
| 用户说「仅修改已有脚手架中的 X」 | 不跑 Phase 0–4，直接改文件 |
| 用户问「项目状态」 | 读 `docs/post-scaffold-status.md`，不跑 intake |
