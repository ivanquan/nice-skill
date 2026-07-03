---
name: "windows-dev-bootstrap"
description: "一键初始化 Windows 爬虫开发环境：安装软件、配置 Node.js/Python/Docker、设置系统环境变量。"
---

# Windows Dev Bootstrap

一键配置新电脑的爬虫开发环境。基于 winget + NVM + pip，覆盖 IDE、数据库、抓包工具、效率工具等全栈。

## 工作流（4 阶段）

### 阶段 1：生成软件清单

根据用户角色（默认：爬虫工程师）和偏好，确认要安装的软件。

- 读取 `references/packages.md` 获取默认清单
- 展示给用户确认，允许添加/移除
- 用户可以通过对话自定义（"去掉 Navicat"、"加个 Postman"）

### 阶段 2：环境检测

运行检测脚本，看哪些已安装、哪些缺失。

```powershell
# 检测 winget 可用性
winget --version

# 检测已安装的关键软件
$packages = @(
    "Git.Git", "Anysphere.Cursor", "JetBrains.PyCharm.Community",
    "Microsoft.VisualStudioCode", "Oracle.MySQL", "MongoDB.Server",
    "PremiumSoft.NavicatPremium", "Redis.Redis", "Ruihu.Apifox",
    "XK72.Charles", "appmakes.Typora", "PixPin.PixPin",
    "xishang0128.Sparkle", "Docker.DockerDesktop"
)
foreach ($pkg in $packages) {
    $installed = winget list --id $pkg --accept-source-agreements 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "✅ $pkg" } else { Write-Host "❌ $pkg" }
}
```

- 检测 Node.js（nvm list）、Python（python --version）
- 检测 PATH 是否包含必要路径
- 输出缺失清单

### 阶段 3：批量安装

按依赖顺序安装所有缺失软件。

#### 安装顺序（重要！）

1. **基础工具**：Git, Python → 先装，后续可能依赖
2. **IDE**：VS Code, Cursor, PyCharm CE
3. **数据库**：MySQL, MongoDB, Redis, Navicat
4. **抓包/调试**：Charles, Apifox
5. **效率工具**：Typora, PixPin, Sparkle
6. **容器**：Docker Desktop
7. **Node 环境**：NVM → Node LTS + 最新版

#### 安装命令模板

```powershell
# 通用 winget 安装
winget install --id <PackageId> --accept-source-agreements --accept-package-agreements -h

# Python 额外步骤：pip 配置国内镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# NVM for Windows
# 下载并安装 nvm-setup.exe
# 然后用 nvm 安装 Node
nvm install lts
nvm install latest
nvm use lts

# npm 全局包
npm install -g pnpm yarn typescript ts-node

# npm 镜像源
npm config set registry https://registry.npmmirror.com
```

#### 安装原则

- **幂等**：先检测再安装，已装跳过
- **静默**：winget 用 `-h` 静默模式，减少弹窗
- **汇报进度**：每完成一个软件汇报一次
- **错误处理**：单个失败不中断，最后汇总

### 阶段 4：系统配置与验证

```powershell
# Git 全局配置
git config --global user.name "<用户名>"
git config --global user.email "<邮箱>"

# 验证安装
$verifications = @(
    @{Cmd="git --version"; Name="Git"},
    @{Cmd="python --version"; Name="Python"},
    @{Cmd="nvm version"; Name="NVM"},
    @{Cmd="node --version"; Name="Node.js"},
    @{Cmd="npm --version"; Name="npm"},
    @{Cmd="pnpm --version"; Name="pnpm"},
    @{Cmd="docker --version"; Name="Docker"}
)
foreach ($v in $verifications) {
    $result = Invoke-Expression $v.Cmd 2>$null
    if ($result) { Write-Host "✅ $($v.Name): $result" }
    else { Write-Host "❌ $($v.Name): 未安装" }
}
```

### 完整安装流程

1. 询问用户角色和偏好 → 生成安装清单
2. 询问 Git 用户名/邮箱（用于配置）
3. 运行环境检测 → 展示缺失清单
4. 用户确认 → 开始安装
5. 安装期间汇报进度（✅ Git 2.53、⏳ VS Code 安装中...）
6. 全部完成后验证
7. 给出总结（安装数量、耗时、仍需手动处理的部分）

## 注意事项

- **管理员权限**：部分软件（MySQL、Docker）需要管理员权限，安装前提醒
- **Docker**：需要开启 Hyper-V 或 WSL2，首次安装后需重启
- **MongoDB**：winget 装的是 MongoDB Server，如需 Compass GUI 需单独装 `MongoDB.Compass`
- **Navicat**：winget 装的是试用版，正式版需手动激活
- **Charles**：需要手动安装 SSL 证书才能抓 HTTPS
- **Sparkle**：代理工具，安装后需手动配置订阅

## 主机兼容性

- **Windows 10 build 1809+** 或 **Windows 11**
- 需要 winget（Windows 10 可能需要手动安装 App Installer）
- 部分软件（如 Docker）需要专业版/企业版
