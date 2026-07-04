# nice-skill

个人 Cursor Agent Skills 合集，面向 **JS 逆向 / 协议还原 / 爬虫架构 / 开发环境** 等场景。

仓库地址：[ivanquan/nice-skill](https://github.com/ivanquan/nice-skill)

## 目录结构

```
nice-skill/
├── js-reverse/          # JS 逆向与协议还原
├── spider/              # 爬虫架构与脚手架
├── meta/                # Skill 创建与优化
└── windows-dev-bootstrap/  # Windows 开发环境一键初始化
```

## Skill 索引

### JS 逆向 (`js-reverse/`)

| Skill | 说明 |
|-------|------|
| [web-protocol-recovery](js-reverse/web-protocol-recovery/) | 端到端协议还原，产出 browser-free 的 Python 采集器 |
| [ast-deobfuscate](js-reverse/ast-deobfuscate/) | Babel AST 结构化解混淆（sojson / obfuscator / awsc 等） |
| [env-patch](js-reverse/env-patch/) | Node.js 沙箱补环境，跑通浏览器 JS |
| [browser-hook-snippets](js-reverse/browser-hook-snippets/) | DevTools 观察型 hook 脚本（xhr/fetch/cookie 等） |
| [rs-reverse](js-reverse/rs-reverse/) | 瑞数轻量项目骨架与材料缓存 |
| [captcha-slide-reverse](js-reverse/captcha-slide-reverse/) | 滑块验证码协议还原（极验/腾讯/易盾等） |
| [dy-ab-pure](js-reverse/dy-ab-pure/) | 抖音 Web `a_bogus` 纯 Python 纯算 |

**推荐工作流：**

```
观察/抓包 → browser-hook-snippets
    ↓
协议还原 → web-protocol-recovery
    ↓
解混淆   → ast-deobfuscate
    ↓
补环境   → env-patch / rs-reverse
    ↓
专项     → captcha-slide-reverse / dy-ab-pure
```

### 爬虫 (`spider/`)

| Skill | 说明 |
|-------|------|
| [spider-architect](spider/spider-architect/) | 企业级爬虫架构师，逐 Phase 对齐后生成 Feapder 脚手架 |

### Meta (`meta/`)

| Skill | 说明 |
|-------|------|
| [skill-creator](meta/skill-creator/) | 创建、修订、评测与打包 OpenCode/Cursor Skills |
| [darwin-skill](meta/darwin-skill/) | Skill 自动优化器（SkillLens 9 维评分 + 爬山迭代） |

### 开发环境

| Skill | 说明 |
|-------|------|
| [windows-dev-bootstrap](windows-dev-bootstrap/) | Windows 爬虫开发环境异步初始化（winget / NVM / Docker / IDE） |

## 安装到 Cursor

将需要的 skill 目录复制到 Cursor 个人 skills 目录：

**Windows**

```powershell
# 示例：安装 web-protocol-recovery
Copy-Item -Recurse "js-reverse\web-protocol-recovery" "$env:USERPROFILE\.cursor\skills\web-protocol-recovery"

# 批量安装全部 js-reverse skills
Get-ChildItem "js-reverse" -Directory | ForEach-Object {
  Copy-Item -Recurse $_.FullName "$env:USERPROFILE\.cursor\skills\$($_.Name)" -Force
}
```

**macOS / Linux**

```bash
cp -r js-reverse/web-protocol-recovery ~/.cursor/skills/
```

安装后重启 Cursor 或开启新对话，Agent 会根据 `SKILL.md` 的 `description` 自动匹配触发。

## 不包含的内容

- `~/.cursor/skills-cursor/` 下的 Cursor 内置 skills（由 Cursor 管理，勿手动复制）
- Anthropic 官方 document-skills 插件包

## 维护说明

- 本地主副本：`~/.cursor/skills/`
- 同步到本仓库后 `git push` 即可分享与备份
- 每个 skill 以 `SKILL.md` 为入口，可附带 `references/`、`scripts/`、`assets/`、`evals/` 等
