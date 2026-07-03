---
name: "windows-dev-bootstrap"
description: "异步初始化 Windows 爬虫开发环境：后台安装软件、配置 Node.js/Python/Docker、设置系统环境变量、JetBrains IDE 激活。"
---

# Windows Dev Bootstrap（异步模式）

一键配置新电脑的爬虫开发环境。基于 winget + NVM + pip，覆盖 IDE、数据库、抓包工具、效率工具等全栈。

**核心原则：异步执行，不阻塞会话。**

## 异步工作流（3 阶段）

### 阶段 1：生成软件清单 & 收集配置

根据用户角色（默认：爬虫工程师）和偏好，确认要安装的软件。

- 读取 `references/packages.md` 获取默认清单
- 展示给用户确认，允许添加/移除
- 用户可以通过对话自定义（"去掉 Navicat"、"加个 Postman"）
- **一次性**收集 Git 用户名/邮箱

输出格式：Markdown 表格展示清单 + 分类汇总。

### 阶段 2：环境检测（同步，快速）

运行 `scripts/check-env.ps1` 检测已安装软件和缺失项。

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/check-env.ps1"
```

- 输出缺失清单
- 用户确认后，进入异步安装阶段
- **提醒**：MySQL、Docker 需要管理员权限，确认当前终端是否以管理员运行

### 阶段 3：异步批量安装

**核心变化：不逐阶段等待，所有任务通过子任务/后台进程并行推进。**

#### 3a. 创建安装任务计划

根据确认的清单，生成一个 `install-plan.json`（写入临时文件），包含：
- 要安装的 winget 包列表（按优先级）
- npm 全局包列表
- pip 包列表
- 镜像源配置项
- Git 配置信息

#### 3b. 启动异步安装

使用 **sessions_spawn** 派生子 agent 执行安装脚本，立即返回控制权：

```
sessions_spawn(
  task: "运行 bootstrap.ps1 完成所有软件安装...",
  taskName: "bootstrap-install",
  mode: "run"
)
```

子 agent 任务描述模板：

```
你是 Windows 环境安装脚本执行器。请执行以下步骤完成开发环境安装：

1. 运行 PowerShell 脚本：powershell -ExecutionPolicy Bypass -File "scripts/bootstrap.ps1"
2. 所有 winget 安装会自动跳过已安装的包（幂等）
3. 脚本会自动处理 pip/npm 镜像源配置
4. 脚本末尾会打印安装总结（成功数、失败数、耗时）
5. 等待脚本完成，汇报结果

工作目录：C:\Users\yafex\.openclaw\workspace\skills\windows-dev-bootstrap

注意事项：
- 部分软件（MySQL、Docker）需要管理员权限
- 如果 winget install 失败，记录下来继续
- NVM 安装后需要刷新环境变量，脚本已处理
- 完成后请用简洁的总结告知安装了哪些、失败了哪些
```

#### 3c. 汇报状态（异步）

子 agent 启动后，立即向用户汇报：

```
安装任务已在后台启动（任务ID: bootstrap-install）。

当前状态：后台运行中，包括：
- winget 安装 XX 个软件包
- npm 全局包 XX 个
- pip 包 XX 个
- 镜像源配置

你可以继续其他工作，安装完成后我会通知你。
```

#### 3d. 完成后处理

子 agent 完成后，用户会收到通知。此时可以运行验证：

```powershell
# 快速验证关键工具
$tools = @("git", "python", "node", "npm", "pnpm", "docker")
foreach ($t in $tools) {
    $v = & $t --version 2>$null
    if ($v) { Write-Host "✅ $t $v" } else { Write-Host "❌ $t 不可用" }
}
```

## 子任务（sessions_spawn）模式说明

### 何时用 sessions_spawn

| 场景 | 模式 |
|------|------|
| 全量安装（默认） | 1 个子 agent 执行完整 `bootstrap.ps1` |
| 只需要装特定分类 | 可以拆分为多个子 agent（如 IDE 一个、数据库一个） |
| 用户中途追加安装 | 新的子 agent 执行追加的包 |

### 子任务模板

```
spawn 任务名: "bootstrap-install"
说明: 执行 scripts/bootstrap.ps1 完成所有软件安装
预期输出: 安装成功/失败列表，耗时
```

如果用户要求并行安装不同分类（不推荐，winget 不支持并发），可以拆分为：

```
- "bootstrap-core": Git + Python + NVM + Node
- "bootstrap-ide": Cursor + PyCharm + VS Code  
- "bootstrap-db": MySQL + MongoDB + Redis + Navicat
- "bootstrap-tools": Apifox + Charles + Typora + 其他
- "bootstrap-docker": Docker Desktop
- "pip-install": pip packages
```

**建议**：先用一个子 agent 跑完整脚本（winget 顺序安装最稳定），失败的部分再单独重试。

## 安装顺序

脚本 `bootstrap.ps1` 内部已按以下顺序执行：

1. **核心工具**：Git, Python 3.12 → 配置 pip 镜像
2. **IDE**：VS Code, Cursor, PyCharm CE
3. **数据库**：MySQL, MongoDB, Redis, Navicat
4. **调试工具**：Apifox, Charles
5. **效率工具**：Typora, PixPin, Sparkle, 微信等
6. **容器**：Docker Desktop
7. **Node 环境**：NVM → Node LTS → npm 镜像 → 全局包

## 阶段 4：JetBrains IDE 激活（PyCharm 等）

PyCharm 安装完成后，需要运行激活脚本来完成破解。激活脚本位于 `scripts/` 目录下。

### 前置条件

1. PyCharm 已通过 winget 安装完成
2. `scripts/micool_config/` 目录下存在激活配置文件（`_auto`、`JetBrains`、`JetBrainsold`、`JetBrainscode` 子目录）
3. **关闭所有正在运行的 JetBrains IDE**（包括 PyCharm、Toolbox 等）

### 文件说明

| 文件 | 用途 | 使用方式 |
|------|------|----------|
| `scripts/jetbrains-activate.cmd` | 主激活脚本，复制破解文件 + 修改 hosts | 右击 → **以管理员身份运行** |
| `scripts/jetbrains-activate-silent.vbs` | 静默启动包装器，后台运行激活脚本 | **双击打开**（无需手动右键管理员） |
| `scripts/micool_config/` | 激活所需的配置文件目录 | 由激活脚本自动读取 |

### 激活流程（异步）

在阶段 3 的安装子 agent 完成后，自动或手动触发激活：

#### 方式 A：手动激活（推荐首次使用）

1. 确保 PyCharm 已安装且关闭
2. 双击 `scripts/jetbrains-activate-silent.vbs`
   - 这个 VBS 脚本会静默调用 `jetbrains-activate.cmd`
   - CMD 脚本会自动提权到管理员模式
3. 等待脚本执行完毕（会自动弹出完成提示）
4. 打开 PyCharm，确认激活状态

#### 方式 B：通过子 agent 异步执行

```
sessions_spawn(
  task: "以管理员身份运行 scripts/jetbrains-activate.cmd，等待完成并汇报结果",
  taskName: "jetbrains-activate",
  mode: "run"
)
```

子 agent 任务描述：

```
你是 JetBrains 激活脚本执行器。请执行以下步骤：

1. 关闭所有正在运行的 JetBrains IDE（如果正在运行）
2. 以管理员身份运行激活脚本：
   powershell -Command "Start-Process -FilePath 'scripts/jetbrains-activate.cmd' -Verb RunAs -Wait"
3. 等待脚本完成，确认输出中显示"激活成功"
4. 汇报结果

工作目录：C:\Users\yafex\.openclaw\workspace\skills\windows-dev-bootstrap

注意事项：
- 杀毒软件可能会拦截，需要提前添加信任或暂时关闭
- 脚本会修改 C:\Windows\System32\drivers\etc\hosts 文件
- 如果 PyCharm 之前从未启动过，需要先启动一次再关闭，然后运行激活
```

### 激活脚本做了什么

1. 清理 JetBrains Toolbox 旧许可文件
2. 将 `micool_config` 中的激活配置复制到系统目录
3. 分别处理 2017-2022 各版本的 JetBrains 产品
4. 修改 hosts 文件屏蔽 JetBrains 激活验证服务器：
   - `0.0.0.0 account.jetbrains.com`
   - `0.0.0.0 oauth.account.jetbrains.com`
   - `0.0.0.0 jrebel.npegeek.com`
5. 刷新 DNS 缓存
6. 备份激活码到 `C:\激活码_备用`

### 注意事项

- **杀毒软件**：激活脚本会被部分杀毒软件误报，运行前可能需要添加排除项或暂时关闭实时防护
- **管理员权限**：脚本需要管理员权限（修改 hosts + 写入系统目录），VBS 包装器会自动触发 UAC 提权
- **PyCharm 首次启动**：如果 PyCharm 从未启动过，先启动一次让它在 `%APPDATA%\JetBrains` 创建配置目录，然后关闭再运行激活
- **Toolbox 用户**：如果安装了 JetBrains Toolbox，激活脚本会清理 Toolbox 的许可缓存
- **hosts 备份**：脚本会自动备份 hosts 文件到 `C:\Windows\System32\drivers\etc\hosts.bak\`

## 安装原则

- **幂等**：先检测再安装，已装跳过
- **静默**：winget 用 `-h` 静默模式
- **错误不中断**：单个失败不中断整体
- **异步不阻塞**：agent 不等待安装完成，由子任务汇报结果

## 注意事项

- **管理员权限**：MySQL、Docker 安装需要管理员权限，非管理员环境会安装失败（脚本会标记为 failed）
- **Docker**：需要开启 Hyper-V 或 WSL2，首次安装后需重启
- **MongoDB**：winget 装的是 MongoDB Server，Compass GUI 需另装 `MongoDB.Compass`
- **Navicat**：winget 装的是试用版，正式版需手动激活
- **Charles**：需要手动安装 SSL 证书才能抓 HTTPS
- **Sparkle**：代理工具，安装后需手动配置订阅
- **终端重启**：NVM/Node 安装后可能需要新开终端才能生效

## 主机兼容性

- Windows 10 build 1809+ 或 Windows 11
- 需要 winget
- 部分软件（Docker）需要专业版/企业版
