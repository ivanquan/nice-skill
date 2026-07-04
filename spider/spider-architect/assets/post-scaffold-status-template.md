# 落地后状态跟踪（Post-Scaffold Status）

> 由 spider-architect Phase 5 生成，Phase 6 逐步勾选更新。
> **当前总状态**：🟡 待配置 | 🟠 待完善 | 🟢 待测试 | ✅ 可交付

---

## 项目信息

| 项 | 值 |
|----|-----|
| 项目名称 | {PROJECT_NAME} |
| 路径 | {PROJECT_PATH} |
| Feapder 模式 | {FEAPDER_MODE} |
| 生成时间 | {DATE} |

---

## Phase 6A：待配置（CONFIGURE）

| 序号 | 配置项 | 状态 | 验证记录 |
|------|--------|------|----------|
| C1 | Python 依赖 `requirements.txt` | ☐ | |
| C2 | `.env` 从 `.env.example` 创建 | ☐ | |
| C3 | 代理 PROXY_HTTP / PROXY_HTTPS | ☐ | |
| C4 | Cookie API（及鉴权若有） | ☐ | |
| C5 | Redis 连接 | ☐ | |
| C6 | MySQL 建库 + `docs/schema.sql` | ☐ | |
| C7 | MongoDB 连接 | ☐ | |
| C8 | 其他 API Key（打码等） | ☐ / N/A | |
| C9 | Feapder 线程/重试等参数 | ☐ | |
| C10 | 部署机网络可达（内网 API） | ☐ | |

**CHECKPOINT-6A**：☐ 未通过 / ☑ 已通过

---

## Phase 6B：待完善（COMPLETE）

### 阻塞运行（必须处理）

| 文件 | 说明 | 状态 |
|------|------|------|
| {BLOCKER_1} | | ☐ |

### 功能增强 / Hook（可分期）

| 文件 | 类型 | 说明 | 转交 Skill | 状态 |
|------|------|------|------------|------|
| parsers/*.py | 骨架 | 需真实 HTML 校准 | — | ☐ |
| utils/sign_helper.py | HOOK | L3+ 签名 | web-protocol-recovery | ☐ / N/A |

**CHECKPOINT-6B**：☐ 未通过 / ☑ 已通过

---

## Phase 6C：测试（TEST）

| 用例 | 名称 | 状态 | 备注 |
|------|------|------|------|
| T1 | 冒烟（API/Redis/单任务） | ☐ | |
| T2 | 功能（多站点 keyword+asin） | ☐ | |
| T3 | 异常（重试/挑战页） | ☐ | |
| T4 | 小规模压测 | ☐ | |

**CHECKPOINT-6C**：☐ 未通过 / ☑ 已通过

---

## Skill 转交表（运行期）

| 待实现项 | 位置 | Skill | 优先级 |
|----------|------|-------|--------|
| | | | |

---

## 变更记录

| 日期 | 阶段 | 说明 |
|------|------|------|
| {DATE} | Phase 5 | 脚手架生成 |
