# 软件清单（windows-dev-bootstrap）

> 安装根目录：`D:\worksoft`
> 来源优先级：`winget` → `scoop` → `direct`（官方直下）→ 手动
> 所有安装均合法，**不含任何破解/激活组件**。

## 核心工具

| 软件 | winget id | scoop | 官方直下 | 备注 |
|---|---|---|---|---|
| Git | `Git.Git` | `git` | — | — |
| Python 3.12 | `Python.Python.3.12` | `python`（仅最新版） | python.org | 需 3.9–3.11 请用官方安装包静默装（`/quiet TargetDir= PrependPath=0`） |
| pip 镜像 | — | — | — | 自动设清华源 `pypi.tuna.tsinghua.edu.cn` |

## IDE

| 软件 | winget id | scoop | 官方直下 | 备注 |
|---|---|---|---|---|
| VS Code | `Microsoft.VisualStudioCode` | `vscode` | — | — |
| Cursor | `Anysphere.Cursor` | `cursor` | https://download.cursor.com/latest/win | — |
| PyCharm 社区版 | `JetBrains.PyCharm.Community` | `pycharm` | — | 免费 |
| PyCharm 专业版 | — | — | jetbrains.com/pycharm/download | **需正版许可**，本 skill 不提供任何破解 |

## 数据库

| 软件 | winget id | scoop | 官方直下 | 备注 |
|---|---|---|---|---|
| MySQL | `Oracle.MySQL` | （无） | cdn.mysql.com/Downloads/MySQL-9.7 | 非管理员走官方 ZIP + VC++ 运行库兜底（见 SKILL.md 坑 B） |
| MongoDB Server | `MongoDB.Server` | `mongodb` | — | 858MB+，注册服务需管理员 |
| MongoDB Compass | `MongoDB.Compass` | `mongodb-compass` | — | GUI |
| Redis | `Redis.Redis` | `redis` | — | MSYS 编译版，配置用相对路径（见坑 C） |
| Redis Insight | `RedisInsight.RedisInsight` | （无） | redis.com/redis-insight | 官方直下 |
| Another Redis Desktop Manager | `qishibo.AnotherRedisDesktopManager` | `another-redis-desktop-manager` | — | — |
| Navicat Premium | `PremiumSoft.NavicatPremium` | （无） | download.navicat.com | 试用；正式需许可 |

## 调试 / 抓包

| 软件 | winget id | scoop | 官方直下 | 备注 |
|---|---|---|---|---|
| Apifox | `Ruihu.Apifox` | `apifox` | — | — |
| Charles | `XK72.Charles` | （无） | charlesproxy.com（Charles64.msi） | 需手动装 SSL 证书抓 HTTPS |

## 效率工具

| 软件 | winget id | scoop | 官方直下 | 备注 |
|---|---|---|---|---|
| Typora | `appmakes.Typora` | `typora` | — | — |
| PixPin | `PixPin.PixPin` | `pixpin` | — | 自带 VS2022 运行库，可作 MySQL 运行库兜底来源 |
| Sparkle | `xishang0128.Sparkle` | `sparkle` | — | 代理，需配订阅 |
| CC Switch | `farion1231.CC-Switch` | `cc-switch` | — | — |
| 百度网盘 | `Baidu.BaiduNetdisk` | `baidunetdisk` | — | — |
| uTools | `Yuanli.uTools` | `utools` | — | — |
| 微信 | `Tencent.WeChat` | `wechat` | — | — |
| 向日葵 | `XPDDRBQ2D1N7NJ` | （无） | oray.com（SunLoginClient.exe） | 远程控制 |
| Proxifier | `VentoByte.Proxifier` | （无） | proxifier.com | — |
| Clash Verge Rev | `ClashVergeRev.ClashVergeRev` | `clash-verge-rev` | — | — |
| SpaceSniffer | `UderzoSoftware.SpaceSniffer` | `spacesniffer` | — | — |

## 容器

| 软件 | winget id | scoop | 官方直下 | 备注 |
|---|---|---|---|---|
| Docker Desktop | `Docker.DockerDesktop` | （CLI 用 `docker`） | — | 需 WSL2/Hyper-V + 管理员 + 重启 |

## Node 环境

| 组件 | 来源 | 备注 |
|---|---|---|
| NVM for Windows | `CoreyButler.NVMforWindows` / `nvm` | 装后需新开终端 |
| Node LTS | `nvm install lts` | — |
| npm 镜像 | `registry.npmmirror.com` | 自动设置 |
| 全局包 | `pnpm` `yarn` `typescript` `ts-node` `tsx` | — |

## 安装后手动事项

1. Docker Desktop：重启并启用 WSL2/Hyper-V（需管理员）
2. Charles：Help → SSL Proxying 安装证书
3. Navicat / PyCharm 专业版：用正版许可激活
4. Sparkle / Proxifier / CC Switch：配置订阅
5. pip 依赖：`pip install scrapy requests httpx aiohttp selenium playwright beautifulsoup4 lxml pandas`
6. Playwright 浏览器：`playwright install chromium`
