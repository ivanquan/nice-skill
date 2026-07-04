# 站点画像（扩展占位）

V1 不内置具体站点画像。本文件保留扩展接口，供后续版本添加 TikTok、Facebook、Instagram、YouTube 等画像。

## 何时读取

- Phase 1 反爬分析时，若本文件已有目标站点条目，优先加载。
- V1 无条目时，跳过本文件，基于用户输入材料和 [decision-matrix.md](decision-matrix.md) 通用框架分析。

## 画像条目模板（添加时使用）

每个站点一个 `## {站点名}` 块，包含：

```markdown
## {站点名}

- **域名**：example.com
- **反爬等级**：L?
- **关键机制**：[列表]
- **推荐策略**：协议逆向 | Feapder 纯接口 | Feapder+Playwright
- **逆向 Skill 路由**：[列表]
- **已知 API 模式**：[路径规律、参数说明]
- **常见坑**：[列表]
- **最后更新**：YYYY-MM-DD
```

## 添加新画像的流程

1. 用户或运维提供经过验证的站点分析材料。
2. 按模板写入本文件。
3. 同步更新 `evals/evals.json` 增加触发用例。
4. 运行 `skill-creator` 的 description 优化（可选）。

## V2 计划站点

以下站点计划在 V2 添加内置画像（V1 不实现）：

- TikTok（a_bogus/BDMS → `dy-ab-pure`）
- Facebook（Cookie 链/GraphQL）
- Instagram（同 FB 生态）
- YouTube（Protobuf/InnerTube API）

V1 分析这些站点时，使用通用 L3–L4 框架 + 用户提供的具体材料，并在架构文档中标注「待 V2 站点画像补充」。
