# 爬虫工程师软件清单

## 核心环境

| 分类 | 软件 | winget ID | 安装方式 | 备注 |
|------|------|-----------|----------|------|
| 语言 | Python 3.12 | `Python.Python.3.12` | winget | 自动加入 PATH |
| 语言 | Node.js | 通过 NVM 管理 | NVM 脚本 | 不直接 winget 装 |
| 版本管理 | NVM for Windows | `CoreyButler.NVMforWindows` | winget | Node 版本切换 |

## IDE

| 软件 | winget ID | 备注 |
|------|-----------|------|
| Cursor | `Anysphere.Cursor` | AI 编辑器 |
| PyCharm CE | `JetBrains.PyCharm.Community` | Python IDE，安装后运行 `scripts/jetbrains-activate-silent.vbs` 激活 |
| VS Code | `Microsoft.VisualStudioCode` | 轻量编辑器 |

## 数据库

| 软件 | winget ID | 备注 |
|------|-----------|------|
| MySQL | `Oracle.MySQL` | 关系型数据库 |
| MongoDB | `MongoDB.Server` | NoSQL 文档数据库 |
| MongoDB Compass | `MongoDB.Compass` | MongoDB GUI |
| Navicat Premium | `PremiumSoft.NavicatPremium` | 数据库 GUI |
| Redis | `Redis.Redis` | 缓存/队列 |
| Redis Insight | `RedisInsight.RedisInsight` | Redis GUI |
| RedisDesktopManager | `qishibo.AnotherRedisDesktopManager` | Redis 桌面管理 |

## 抓包与调试

| 软件 | winget ID | 备注 |
|------|-----------|------|
| Apifox | `Ruihu.Apifox` | 接口调试 |
| Charles | `XK72.Charles` | HTTP/HTTPS 抓包 |

## 效率工具

| 软件 | winget ID | 备注 |
|------|-----------|------|
| Typora | `appmakes.Typora` | Markdown 编辑器 |
| PixPin | `PixPin.PixPin` | 截图/贴图/OCR |
| Sparkle | `xishang0128.Sparkle` | 网络代理 |
| CC Switch | `farion1231.CC-Switch` | 代理切换工具 |
| WeChat | `Tencent.WeChat` | 微信 |
| Sunlogin | `XPDDRBQ2D1N7NJ` (msstore) | 向日葵远程 |
| Baidu Netdisk | `Baidu.BaiduNetdisk` | 百度网盘 |
| uTools | `Yuanli.uTools` | 效率启动器 |
| Proxifier | `VentoByte.Proxifier` | SOCKS5 代理/强制代理 |
| Clash Verge | `ClashVergeRev.ClashVergeRev` | 代理客户端（Clash Meta GUI） |
| SpaceSniffer | `UderzoSoftware.SpaceSniffer` | 磁盘空间分析 |

## 版本控制与容器

| 软件 | winget ID | 备注 |
|------|-----------|------|
| Git | `Git.Git` | 版本控制 |
| Docker Desktop | `Docker.DockerDesktop` | 容器化 |

## npm 全局包（NVM 安装 Node 后）

```
pnpm
yarn
typescript
ts-node
tsx
```

## pip 全局包

```
scrapy
requests
httpx
aiohttp
selenium
playwright
beautifulsoup4
lxml
pandas
```

## pip 镜像源配置

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## npm 镜像源配置

```bash
npm config set registry https://registry.npmmirror.com
```
