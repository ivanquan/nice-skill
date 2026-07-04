# Phase 6：落地后引导（Post-Scaffold Guide）

> **V1.3**：Phase 5 生成代码后，项目处于「待配置 → 待完善 → 待测试」三态。**禁止**假设脚手架可一键运行。

## 项目状态模型

```
Phase 5 完成
    │
    ▼
🟡 待配置（CONFIGURE）   ──► CHECKPOINT-6A
    │
    ▼
🟠 待完善（COMPLETE）    ──► CHECKPOINT-6B
    │
    ▼
🟢 待测试（TEST）        ──► CHECKPOINT-6C
    │
    ▼
✅ 可交付运行
```

| 状态 | 含义 | Agent 行为 |
|------|------|------------|
| 待配置 | `.env`、DB 建库、依赖未就绪 | **逐步引导**填写配置，逐项验证连通性 |
| 待完善 | Hook 占位、parser 骨架、未实现逻辑 | **扫描清单** + 说明影响；用户确认后再改代码 |
| 待测试 | 配置与代码就绪 | 提供**多场景测试用例**，协助执行与排错 |

---

## Phase 5 结束时必做（进入 Phase 6 的前置输出）

Phase 5 最后一轮回复必须包含：

1. 写入 `docs/post-scaffold-status.md`（从 [post-scaffold-status-template.md](../assets/post-scaffold-status-template.md) 生成）
2. 明确告知：**项目当前为「待配置」，不可直接生产运行**
3. 列出 Phase 6A 第一项待配置，**询问是否开始配置引导**

**禁止**：Phase 5 结束后只说「运行 `python main.py`」而不做状态说明。

---

## Phase 6A：待配置引导（CONFIGURE）

### 执行规则

1. **一次引导一类**（或一项），完成验证后再下一项。
2. 每类配置给出：要改的文件、示例值格式、验证命令、失败时排查点。
3. 敏感信息只写入 `.env`，提醒用户勿提交 Git。
4. 用户说「这项已配好」或验证通过后，在 `post-scaffold-status.md` 勾选并进入下一项。

### 标准配置清单（按顺序）

| 序号 | 类别 | 典型文件/操作 | 验证方式 |
|------|------|---------------|----------|
| C1 | Python 依赖 | `pip install -r requirements.txt` | `python -c "import feapder"` |
| C2 | 环境变量 | 复制 `.env.example` → `.env` | 文件存在且非空关键项 |
| C3 | 代理 | `.env` `PROXY_HTTP/HTTPS` | `curl -x ...` 或脚本测代理 |
| C4 | Cookie/账号 API | `.env` `COOKIE_API_URL` | 请求样本 platform+code 返回 cookie |
| C5 | Redis | `.env` + 服务启动 | `redis-cli ping` 或 redis_client 连接 |
| C6 | MySQL | `.env` + **执行 `docs/schema.sql`** | 建库建表 + `add_smart` 试插入 |
| C7 | MongoDB | `.env` + 服务启动 | `mongo` 连接 + 试 `add` |
| C8 | 打码/其他 API Key | `.env`（若 Phase 0.5 启用） | 按平台文档测一次 |
| C9 | Feapder 运行参数 | `settings.py` / 环境变量 | 线程数、重试次数与预期一致 |
| C10 | 网络/内网 | Cookie API、代理可达 | 从部署服务器 curl |

### Phase 6A 输出模板

```markdown
## 配置进度（CHECKPOINT-6A）

| 项 | 状态 | 备注 |
|----|------|------|
| C1 依赖 | ☐ | |
| ... | | |

**当前引导**：C?_ ...
**请你操作**：...
**验证命令**：...
完成后回复「C?_ 完成」或贴验证结果。
```

🔴 **CHECKPOINT-6A**：清单全部 ☐→☑ 或用户确认跳过某项 → Phase 6B。

---

## Phase 6B：待完善代码引导（COMPLETE）

### 扫描范围（Phase 5 后 Agent 必须执行）

在项目目录内搜索并汇总：

| 标记 | 含义 |
|------|------|
| `# --- SKILL HOOK ---` | 需逆向 Skill 或业务实现 |
| `TODO` / `FIXME` | 脚手架未完成 |
| `NotImplementedError` | 显式未实现 |
| `YOUR_` / `xxx` 占位 | 配置或逻辑占位 |
| `raise NotImplementedError` | 不可运行路径 |
| parser 仅正则骨架 | 需用真实 HTML 回归 |

### 输出《待完善代码清单》

| 文件 | 位置/行 | 类型 | 影响 | 建议动作 | 转交 Skill |
|------|---------|------|------|----------|------------|
| parsers/search_parser.py | 全文 | 骨架 | 字段不全/漏解析 | 用样本 HTML 补全 | — |
| utils/sign_helper.py | HOOK | 占位 | L3+ 接口不可用 | web-protocol-recovery | |

### 执行规则

1. **先清单、后改码**：默认只输出清单；用户说「完善 parser」或「实现 X」才改对应文件。
2. 区分：**阻塞运行**（必须完善） vs **功能增强**（可后补）。
3. 每项完善后更新 `post-scaffold-status.md` 的 COMPLETE 区。

### 常见「脚手架级」待完善项（按项目类型勾选）

| 模块 | 通常状态 | 说明 |
|------|----------|------|
| `parsers/*` | 骨架 | 需目标站真实 HTML 校准 |
| `sign_helper.py` | Hook | L3+ 才需实现 |
| `captcha_middleware.py` | 未生成/Hook | 接打码才需 |
| `account_pool` 登录 | Hook | Cookie API 已覆盖则可标为 N/A |
| Feapder 版本适配 | 可能 | Task/Batch API 差异需联调 |

🔴 **CHECKPOINT-6B**：阻塞项已全部处理或用户接受风险 → Phase 6C。

---

## Phase 6C：测试方案（TEST）

### 前置条件

- CHECKPOINT-6A、6B 已完成（或用户明确「先测再说」）

### 必须提供多档测试用例（至少 4 类）

| 级别 | 目的 | 典型用例 |
|------|------|----------|
| **T1 冒烟** | 链路通 | 健康检查 API、Redis ping、单条 keyword 单页 |
| **T2 功能** | 业务正确 | 每站点 1 条 keyword + 1 ASIN；校验 MySQL 字段 |
| **T3 异常** | 容错 | 故意错误 ASIN、挑战页样本、代理失败重试入队 |
| **T4 小规模压测** | 性能 | N 并发 / M 条任务，观察 403 率与队列积压 |

### 测试用例文档格式

每个用例包含：

```markdown
### T?_ {名称}
- **目的**：
- **前置**：已配置项 C?
- **步骤**：
  1. ...
- **命令/请求**：（可复制）
- **预期结果**：
- **失败排查**：
```

### 执行规则

1. 建议顺序：T1 → T2 → T3 → T4。
2. 用户执行后贴日志/报错，Agent 协助排错，**不跳过 Phase 6A 的配置问题**。
3. 全部通过后更新 `post-scaffold-status.md` 为 **✅ 可交付运行**。

🔴 **CHECKPOINT-6C**：关键用例通过 → 项目交付完成。

---

## 与用户对话话术

Phase 5 结束：

```markdown
脚手架已生成。当前状态：**🟡 待配置**（不可直接生产运行）。

已写入 `docs/post-scaffold-status.md`。
是否从 **C1 安装依赖** 开始逐步配置？回复「开始配置引导」。
```

Phase 6A 每一项：

```markdown
### 当前：C5 Redis
请确认 `.env` 中 REDIS_HOST/PORT，并执行验证命令：...
完成后回复「C5 完成」。
```

Phase 6B：

```markdown
《待完善代码清单》共 N 项，其中阻塞运行 M 项。
是否优先完善 parsers？回复要处理的文件或「先测 T1」。
```

Phase 6C：

```markdown
配置与代码就绪后，建议按 T1→T2→T3→T4 测试。
先从 T1 冒烟开始？回复「执行 T1」获取具体命令。
```

---

## 例外

| 场景 | 行为 |
|------|------|
| 用户「只改 parser」 | 跳过 6A/6C，仅 6B 清单 + 改码 |
| 用户「跳过配置先测」 | 标注风险，仅给 T1，并提醒未配 DB 会失败 |
| 用户「项目已跑通，补测试文档」 | 仅 Phase 6C |
