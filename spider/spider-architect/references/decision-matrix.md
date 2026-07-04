# 抓取策略决策矩阵

## 反爬等级定义

| 等级 | 名称 | 典型机制 | 检测信号 |
|---|---|---|---|
| L1 | 开放 | 无/sign、静态 HTML | 直接请求 200 |
| L2 | 轻防护 | Cookie/Referer/UA | 缺 Header 403 |
| L3 | 动态签名 | a_bogus、mstoken、x-sign | 缺 sign 空响应 |
| L4 | 态依赖 | 指纹、Cookie 链、Session 绑定 | 跨 IP Cookie 失效 |
| L5 | 重度防护 | WASM、瑞数、Cloudflare、验证码 | 412/403 challenge |

## 策略 × 等级矩阵

| 反爬等级 | 首选策略 | Feapder 运行模式 | 逆向 Skill |
|---|---|---|---|
| L1 | Feapder 纯接口 | AirSpider 可满足 | 无 |
| L2 | Feapder + Middleware | Air/Batch 视规模 | 可选 hook 观察 |
| L3 | 协议逆向 | Batch/Task 生产 | `web-protocol-recovery` / `dy-ab-pure` |
| L4 | 混合取态 | Batch + Playwright | `web-protocol-recovery` |
| L5 | 混合 + 专项 | Batch + 专项模块 | 见 L5 路由表 |

## L5 机制路由

| 机制 | 转交 Skill |
|---|---|
| 瑞数/Ruishu/Rivers | `rs-reverse` |
| 滑块验证码 | `captcha-slide-reverse` |
| sign 入口不明 | `camoufox-js-reverse` → `ast-deobfuscate` |
| Node 补环境 sign | `env-patch` |
| WASM/JSVMP | `web-protocol-recovery` |
| Cloudflare | `web-protocol-recovery` + Playwright 混合 |

## 三种抓取模式判定

### 模式 A：协议逆向

- API 稳定，sign 可离线生成
- 目标 browser-free
- 脚手架：`utils/sign_helper.py` + Skill Hook

### 模式 B：Feapder 纯接口

- L1–L2，或 L3 sign 已就绪
- Middleware 维护 Cookie/Header

### 模式 C：Feapder + Playwright 混合

- 浏览器取态 → 协议批量抓
- 脚手架：`services/playwright_state.py`

## 决策流程

```
Phase 0: 需求诊断 → feapder_mode (air/batch/task)
        │
        ▼
Phase 1: 反爬等级 L1–L5
        │
        ▼
Phase 2: 抓取策略 A/B/C + 合规风险标注（不拒绝）
        │
        ▼
Phase 3–5: 架构 → 风险 → 脚手架
```

## 常见误判

| 误判 | 纠正 |
|---|---|
| "有 sign 就必须 Playwright" | L3 优先协议逆向 + sign_helper |
| "小规模也用 BatchSpider" | Phase 0 诊断：单次小规模用 AirSpider |
| "合规风险 = 停止设计" | V1.1：标注风险，用户决策 |
| "脚手架 = 签名已实现" | Hook 占位，转交逆向 Skill |
