# Environment Check Script (adaptive: winget / Scoop)
# Detects installed software, package-manager availability, and recommends an approach.
# ASCII only (GBK cmd/pwsh misreads UTF-8 without BOM).

$InstallRoot = "D:\worksoft"

function Test-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-Winget {
    return Get-Command winget -ErrorAction SilentlyContinue
}

function Get-Scoop {
    $s = Get-Command scoop -ErrorAction SilentlyContinue
    if ($s) { return $s }
    # scoop shim may live in a custom root
    $cand = Join-Path $InstallRoot "scoop\shims\scoop.ps1"
    if (Test-Path $cand) { return $cand }
    return $null
}

$isAdmin = Test-Admin
$winget = Get-Winget
$scoop = Get-Scoop

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Environment Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Install root
if (Test-Path $InstallRoot) {
    Write-Host "[Install Root] OK $InstallRoot exists" -ForegroundColor Green
} else {
    Write-Host "[Install Root] MISSING $InstallRoot (will be created)" -ForegroundColor Yellow
}

# Admin
if ($isAdmin) { Write-Host "[Privilege] OK running as Administrator" -ForegroundColor Green }
else { Write-Host "[Privilege] running as standard user (user-mode install only)" -ForegroundColor Yellow }

# Package managers
Write-Host ""
Write-Host "[Package Managers]" -ForegroundColor Yellow
if ($winget) { Write-Host "  OK winget: $(& winget --version 2>$null)" -ForegroundColor Green }
else { Write-Host "  MISSING winget" -ForegroundColor Red }

if ($scoop) { Write-Host "  OK scoop: present" -ForegroundColor Green }
else { Write-Host "  MISSING scoop (bootstrap will install it if winget unavailable)" -ForegroundColor Yellow }

# Recommendation
Write-Host ""
Write-Host "[Recommendation]" -ForegroundColor Magenta
if ($winget -and $isAdmin) {
    Write-Host "  Use WINGET (available + admin). Docker/MySQL service will work." -ForegroundColor Green
} elseif ($winget -and -not $isAdmin) {
    Write-Host "  Use WINGET for apps, but MySQL service / Docker need admin -> they will fall back to portable/auto-start." -ForegroundColor Yellow
} elseif ($scoop) {
    Write-Host "  Use SCOOP (winget missing, scoop present)." -ForegroundColor Green
} else {
    Write-Host "  No winget -> bootstrap will install SCOOP (user-mode, no admin needed)." -ForegroundColor Yellow
}

# Package detection list: Name, WingetId, ScoopName
$packages = @(
    @{Name="Git";                      WingetId="Git.Git";                           Scoop="git"},
    @{Name="Python (latest)";          WingetId="Python.Python.3.12";               Scoop="python"},
    @{Name="VS Code";                  WingetId="Microsoft.VisualStudioCode";        Scoop="vscode"},
    @{Name="Cursor";                   WingetId="Anysphere.Cursor";                  Scoop="cursor"},
    @{Name="PyCharm";                  WingetId="JetBrains.PyCharm.Community";       Scoop="pycharm"},
    @{Name="MySQL";                    WingetId="Oracle.MySQL";                      Scoop=""},
    @{Name="MongoDB";                  WingetId="MongoDB.Server";                    Scoop="mongodb"},
    @{Name="MongoDB Compass";          WingetId="MongoDB.Compass";                   Scoop="mongodb-compass"},
    @{Name="Redis";                    WingetId="Redis.Redis";                       Scoop="redis"},
    @{Name="Redis Insight";            WingetId="RedisInsight.RedisInsight";         Scoop=""},
    @{Name="Another Redis Desktop Mgr";WingetId="qishibo.AnotherRedisDesktopManager";Scoop="another-redis-desktop-manager"},
    @{Name="Navicat Premium";          WingetId="PremiumSoft.NavicatPremium";        Scoop=""},
    @{Name="Apifox";                   WingetId="Ruihu.Apifox";                      Scoop="apifox"},
    @{Name="Charles";                  WingetId="XK72.Charles";                      Scoop=""},
    @{Name="Typora";                   WingetId="appmakes.Typora";                   Scoop="typora"},
    @{Name="PixPin";                   WingetId="PixPin.PixPin";                     Scoop="pixpin"},
    @{Name="Sparkle";                  WingetId="xishang0128.Sparkle";               Scoop="sparkle"},
    @{Name="CC Switch";                WingetId="farion1231.CC-Switch";              Scoop="cc-switch"},
    @{Name="Baidu Netdisk";            WingetId="Baidu.BaiduNetdisk";                Scoop="baidunetdisk"},
    @{Name="uTools";                   WingetId="Yuanli.uTools";                     Scoop="utools"},
    @{Name="WeChat";                   WingetId="Tencent.WeChat";                    Scoop="wechat"},
    @{Name="Sunlogin";                 WingetId="XPDDRBQ2D1N7NJ";                    Scoop=""},
    @{Name="Proxifier";                WingetId="VentoByte.Proxifier";               Scoop=""},
    @{Name="Clash Verge Rev";          WingetId="ClashVergeRev.ClashVergeRev";       Scoop="clash-verge-rev"},
    @{Name="SpaceSniffer";             WingetId="UderzoSoftware.SpaceSniffer";       Scoop="spacesniffer"},
    @{Name="Docker Desktop";           WingetId="Docker.DockerDesktop";              Scoop=""}
)

$installed = @()
$missing = @()

Write-Host ""
Write-Host "[Packages]" -ForegroundColor Yellow
foreach ($pkg in $packages) {
    $found = $false
    if ($winget) {
        winget list --id $pkg.WingetId --accept-source-agreements --exact 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $found = $true }
    }
    if (-not $found -and $scoop -and $pkg.Scoop) {
        & scoop list $pkg.Scoop 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $found = $true }
    }
    if ($found) {
        Write-Host "  OK   $($pkg.Name)" -ForegroundColor Green
        $installed += $pkg.Name
    } else {
        Write-Host "  MISS $($pkg.Name)" -ForegroundColor Red
        $missing += $pkg.Name
    }
}

# NVM / Node
Write-Host ""
Write-Host "[Version Managers / Runtimes]" -ForegroundColor Yellow
$nvm = Get-Command nvm -ErrorAction SilentlyContinue
if ($nvm) { Write-Host "  OK NVM: $(& nvm version 2>$null)" -ForegroundColor Green }
else { Write-Host "  MISS NVM" -ForegroundColor Red; $missing += "NVM" }

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) { Write-Host "  OK Node.js: $(& node --version 2>$null)" -ForegroundColor Green }
else { Write-Host "  MISS Node.js" -ForegroundColor Red }

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installed: $($installed.Count)" -ForegroundColor Green
Write-Host "To install: $($missing.Count)" -ForegroundColor Yellow
if ($missing.Count -gt 0) {
    Write-Host "Missing:" -ForegroundColor Yellow
    foreach ($m in $missing) { Write-Host "  - $m" -ForegroundColor Yellow }
}
