# Windows Dev Environment Bootstrap Script
# Usage: .\bootstrap.ps1 [-SkipCheck]

param(
    [switch]$SkipCheck,
    [string]$Categories = ""
)

$ErrorActionPreference = "Continue"
$startTime = Get-Date
$installed = @()
$failed = @()
$installedCount = 0
$failedCount = 0

function Install-Package {
    param(
        [string]$Name,
        [string]$Id,
        [string]$ExtraArgs = ""
    )

    Write-Host "  ... Installing $Name ..." -NoNewline -ForegroundColor Yellow

    # Check if already installed
    winget list --id $Id --accept-source-agreements --exact 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`r  OK $Name (already installed)" -ForegroundColor Green
        $script:installed += $Name
        $script:installedCount++
        return $true
    }

    $result = winget install --id $Id --accept-source-agreements --accept-package-agreements -h $ExtraArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`r  OK $Name" -ForegroundColor Green
        $script:installed += $Name
        $script:installedCount++
        return $true
    } else {
        Write-Host "`r  FAIL $Name" -ForegroundColor Red
        $script:failed += $Name
        $script:failedCount++
        return $false
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Windows Dev Environment Bootstrap" -ForegroundColor Cyan
Write-Host "  Start: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# === Phase 1: Core Tools ===
Write-Host "[1/7] Core Tools" -ForegroundColor Magenta
Install-Package -Name "Git" -Id "Git.Git"
Install-Package -Name "Python 3.12" -Id "Python.Python.3.12"

# Configure pip mirror
Write-Host "  ... Configuring pip mirror (Tsinghua)..." -NoNewline -ForegroundColor Yellow
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple 2>$null
Write-Host "`r  OK pip mirror configured" -ForegroundColor Green

# === Phase 2: IDEs ===
Write-Host ""
Write-Host "[2/7] IDEs" -ForegroundColor Magenta
Install-Package -Name "VS Code" -Id "Microsoft.VisualStudioCode"
Install-Package -Name "Cursor" -Id "Anysphere.Cursor"
Install-Package -Name "PyCharm CE" -Id "JetBrains.PyCharm.Community"

# === Phase 3: Databases ===
Write-Host ""
Write-Host "[3/7] Databases" -ForegroundColor Magenta
Install-Package -Name "MySQL" -Id "Oracle.MySQL"
Install-Package -Name "MongoDB" -Id "MongoDB.Server"
Install-Package -Name "MongoDB Compass" -Id "MongoDB.Compass"
Install-Package -Name "Redis" -Id "Redis.Redis"
Install-Package -Name "Redis Insight" -Id "RedisInsight.RedisInsight"
Install-Package -Name "RedisDesktopManager" -Id "qishibo.AnotherRedisDesktopManager"
Install-Package -Name "Navicat Premium" -Id "PremiumSoft.NavicatPremium"

# === Phase 4: Debug Tools ===
Write-Host ""
Write-Host "[4/7] Debug Tools" -ForegroundColor Magenta
Install-Package -Name "Apifox" -Id "Ruihu.Apifox"
Install-Package -Name "Charles" -Id "XK72.Charles"

# === Phase 5: Utility Tools ===
Write-Host ""
Write-Host "[5/7] Utility Tools" -ForegroundColor Magenta
Install-Package -Name "Typora" -Id "appmakes.Typora"
Install-Package -Name "PixPin" -Id "PixPin.PixPin"
Install-Package -Name "Sparkle" -Id "xishang0128.Sparkle"
Install-Package -Name "CC Switch" -Id "farion1231.CC-Switch"
Install-Package -Name "Baidu Netdisk" -Id "Baidu.BaiduNetdisk"
Install-Package -Name "uTools" -Id "Yuanli.uTools"
Install-Package -Name "WeChat" -Id "Tencent.WeChat"
Install-Package -Name "Sunlogin" -Id "XPDDRBQ2D1N7NJ"
Install-Package -Name "Proxifier" -Id "VentoByte.Proxifier"
Install-Package -Name "SpaceSniffer" -Id "UderzoSoftware.SpaceSniffer"

# === Phase 6: Container ===
Write-Host ""
Write-Host "[6/7] Container" -ForegroundColor Magenta
Install-Package -Name "Docker Desktop" -Id "Docker.DockerDesktop"

# === Phase 7: Node.js Environment ===
Write-Host ""
Write-Host "[7/7] Node.js Environment" -ForegroundColor Magenta

# NVM for Windows
Install-Package -Name "NVM for Windows" -Id "CoreyButler.NVMforWindows"

# Refresh env vars
Write-Host "  ... Refreshing env vars..." -ForegroundColor Yellow
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Install Node LTS via NVM
Write-Host "  ... Installing Node.js LTS via NVM..." -ForegroundColor Yellow
nvm install lts 2>&1 | Out-Null
nvm use lts 2>&1 | Out-Null
$nv = node --version 2>$null
if ($nv) {
    Write-Host "  OK Node.js: $nv" -ForegroundColor Green
} else {
    Write-Host "  WARN Node.js not found, try restarting terminal" -ForegroundColor Yellow
}

# Configure npm mirror
Write-Host "  ... Configuring npm mirror..." -ForegroundColor Yellow
npm config set registry https://registry.npmmirror.com 2>$null
Write-Host "  OK npm mirror configured" -ForegroundColor Green

# Install global npm packages
Write-Host "  ... Installing global npm packages..." -ForegroundColor Yellow
$npmPkgs = @("pnpm", "yarn", "typescript", "ts-node", "tsx")
foreach ($pkg in $npmPkgs) {
    Write-Host "    Installing $pkg..." -ForegroundColor Gray
    npm install -g $pkg 2>$null
    if ($LASTEXITCODE -eq 0) {
        $v = & $pkg --version 2>$null
        Write-Host "    OK $pkg v$v" -ForegroundColor Green
    } else {
        Write-Host "    FAIL $pkg" -ForegroundColor Red
    }
}

# === Summary ===
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Bootstrap Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Success: $installedCount" -ForegroundColor Green
Write-Host "Failed: $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Green" })
Write-Host "Time: $($duration.TotalMinutes.ToString('0.0')) min" -ForegroundColor Cyan

if ($failedCount -gt 0) {
    Write-Host ""
    Write-Host "Failed items:" -ForegroundColor Red
    foreach ($f in $failed) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Tip: Failed items may be due to network issues. Retry manually later." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Post-install manual steps:" -ForegroundColor Yellow
Write-Host "  1. Docker Desktop: restart PC and enable WSL2/Hyper-V" -ForegroundColor Gray
Write-Host "  2. Charles: install SSL certificate (Help > SSL Proxying)" -ForegroundColor Gray
Write-Host "  3. Navicat: activate license manually" -ForegroundColor Gray
Write-Host "  4. Sparkle: configure subscription URL" -ForegroundColor Gray
Write-Host "  5. pip deps: pip install scrapy requests httpx aiohttp selenium playwright beautifulsoup4 lxml pandas" -ForegroundColor Gray
Write-Host "  6. Playwright browsers: playwright install chromium" -ForegroundColor Gray
