# Environment Check Script
# Checks installed software and toolchains

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Environment Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check winget availability
Write-Host "[Core Tools]" -ForegroundColor Yellow
$wingetVersion = winget --version 2>$null
if ($wingetVersion) {
    Write-Host "  OK winget: $wingetVersion" -ForegroundColor Green
} else {
    Write-Host "  MISSING winget: Please install App Installer" -ForegroundColor Red
}

# Define packages to check
$packages = @(
    @{Id="Git.Git"; Name="Git"; Category="Core"},
    @{Id="Python.Python.3.12"; Name="Python 3.12"; Category="Core"},
    @{Id="Anysphere.Cursor"; Name="Cursor"; Category="IDE"},
    @{Id="JetBrains.PyCharm.Community"; Name="PyCharm CE"; Category="IDE"},
    @{Id="Microsoft.VisualStudioCode"; Name="VS Code"; Category="IDE"},
    @{Id="Oracle.MySQL"; Name="MySQL"; Category="Database"},
    @{Id="MongoDB.Server"; Name="MongoDB"; Category="Database"},
    @{Id="MongoDB.Compass"; Name="MongoDB Compass"; Category="Database"},
    @{Id="PremiumSoft.NavicatPremium"; Name="Navicat Premium"; Category="Database"},
    @{Id="Redis.Redis"; Name="Redis"; Category="Database"},
    @{Id="RedisInsight.RedisInsight"; Name="Redis Insight"; Category="Database"},
    @{Id="qishibo.AnotherRedisDesktopManager"; Name="RedisDesktopManager"; Category="Database"},
    @{Id="Ruihu.Apifox"; Name="Apifox"; Category="Debug"},
    @{Id="XK72.Charles"; Name="Charles"; Category="Debug"},
    @{Id="appmakes.Typora"; Name="Typora"; Category="Utils"},
    @{Id="PixPin.PixPin"; Name="PixPin"; Category="Utils"},
    @{Id="xishang0128.Sparkle"; Name="Sparkle"; Category="Utils"},
    @{Id="farion1231.CC-Switch"; Name="CC Switch"; Category="Utils"},
    @{Id="Baidu.BaiduNetdisk"; Name="Baidu Netdisk"; Category="Utils"},
    @{Id="Yuanli.uTools"; Name="uTools"; Category="Utils"},
    @{Id="Tencent.WeChat"; Name="WeChat"; Category="Utils"},
    @{Id="XPDDRBQ2D1N7NJ"; Name="Sunlogin"; Category="Utils"},
    @{Id="Docker.DockerDesktop"; Name="Docker Desktop"; Category="Container"}
)

$currentCategory = ""
$installed = @()
$missing = @()

foreach ($pkg in $packages) {
    if ($pkg.Category -ne $currentCategory) {
        $currentCategory = $pkg.Category
        Write-Host ""
        Write-Host "[$currentCategory]" -ForegroundColor Yellow
    }

    winget list --id $pkg.Id --accept-source-agreements --exact 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $($pkg.Name)" -ForegroundColor Green
        $installed += $pkg.Name
    } else {
        Write-Host "  MISSING $($pkg.Name)" -ForegroundColor Red
        $missing += $pkg.Name
    }
}

# NVM check
Write-Host ""
Write-Host "[Version Managers]" -ForegroundColor Yellow
$nvmVersion = nvm version 2>$null
if ($nvmVersion) {
    Write-Host "  OK NVM: $nvmVersion" -ForegroundColor Green
    nvm list 2>$null
} else {
    Write-Host "  MISSING NVM" -ForegroundColor Red
    $missing += "NVM for Windows"
}

# Node.js and npm global packages
Write-Host ""
$nodeVersion = node --version 2>$null
if ($nodeVersion) {
    Write-Host "  OK Node.js: $nodeVersion" -ForegroundColor Green
    Write-Host "  Global npm packages:" -ForegroundColor Yellow
    $globalPkgs = @("pnpm", "yarn", "typescript")
    foreach ($p in $globalPkgs) {
        $ver = & $p --version 2>$null
        if ($ver) {
            Write-Host "    OK $p v$ver" -ForegroundColor Green
        } else {
            Write-Host "    MISSING $p" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  MISSING Node.js" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installed: $($installed.Count) packages" -ForegroundColor Green
Write-Host "To install: $($missing.Count) packages" -ForegroundColor Yellow
if ($missing.Count -gt 0) {
    Write-Host "Missing:" -ForegroundColor Yellow
    foreach ($m in $missing) {
        Write-Host "  - $m" -ForegroundColor Yellow
    }
}
