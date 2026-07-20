# Windows Dev Environment Bootstrap (adaptive: winget / Scoop)
# Usage: powershell -ExecutionPolicy Bypass -File bootstrap.ps1 [-SkipCheck] [-Pm auto|winget|scoop]
# ASCII only. No cracks/activation. Installs under D:\worksoft.
# NOTE: JetBrains crack/activation components have been REMOVED. Legitimate install only.

param(
    [switch]$SkipCheck,
    [ValidateSet("auto","winget","scoop")]
    [string]$Pm = "auto"
)

$ErrorActionPreference = "Continue"
$startTime = Get-Date
$InstallRoot = "D:\worksoft"
$installed = @(); $failed = @()
$installedCount = 0; $failedCount = 0

# ---------- helpers ----------
function Test-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Add-UserPath($dir) {
    $cur = [Environment]::GetEnvironmentVariable("Path","User")
    $parts = if ($cur) { $cur -split ";" | Where-Object { $_.Trim() -ne "" } } else { @() }
    if ($parts -notcontains $dir) {
        $parts += $dir
        [Environment]::SetEnvironmentVariable("Path", ($parts -join ";"), "User")
        Write-Host "    OK added to User PATH: $dir" -ForegroundColor Green
    } else { Write-Host "    skip (already in PATH): $dir" -ForegroundColor Gray }
}
function Invoke-Direct($name, $url) {
    if (-not $url) { Write-Host "  MANUAL $name (no direct URL, install manually)" -ForegroundColor Yellow; return $false }
    $tmp = Join-Path $env:TEMP ([IO.Path]::GetFileName($url))
    Write-Host "  ... downloading $name ..." -ForegroundColor Yellow
    try { Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -ErrorAction Stop }
    catch { Write-Host "  FAIL download $name : $_" -ForegroundColor Red; return $false }
    Write-Host "  ... running installer for $name ..." -ForegroundColor Yellow
    Start-Process -FilePath $tmp -ArgumentList "/S" -Wait -ErrorAction SilentlyContinue
    return $true
}

# ---------- install root ----------
if (-not (Test-Path $InstallRoot)) { New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null }

# ---------- select package manager ----------
$isAdmin = Test-Admin
$hasWinget = Get-Command winget -ErrorAction SilentlyContinue
$scoopShim = Join-Path $InstallRoot "scoop\shims\scoop.ps1"
$hasScoop = (Get-Command scoop -ErrorAction SilentlyContinue) -or (Test-Path $scoopShim)

if ($Pm -eq "scoop") { $pm = "scoop" }
elseif ($Pm -eq "winget") { $pm = if ($hasWinget) { "winget" } else { "scoop" } }
else {
    if ($hasWinget -and $isAdmin) { $pm = "winget" }
    elseif ($hasWinget -and -not $isAdmin) { $pm = "winget" }   # apps ok; service tools handled separately
    elseif ($hasScoop) { $pm = "scoop" }
    else { $pm = "scoop" }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Windows Dev Bootstrap  (PM=$pm, admin=$isAdmin)" -ForegroundColor Cyan
Write-Host "  Start: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ---------- ensure Scoop if needed ----------
if ($pm -eq "scoop" -and -not $hasScoop) {
    Write-Host "[setup] Installing Scoop (user-mode) ..." -ForegroundColor Magenta
    $env:SCOOP_SKIP_SAFELY_DELETE = "1"
    [Environment]::SetEnvironmentVariable("SCOOP","$InstallRoot\scoop","User")
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    try { irm get.scoop.sh | iex } catch { Write-Host "  FAIL Scoop install: $_" -ForegroundColor Red; exit 1 }
    scoop bucket add extras 2>$null
    $scoopShim = Join-Path $InstallRoot "scoop\shims\scoop.ps1"
}

# ---------- install functions ----------
function Install-Winget($name, $id, $extra="") {
    winget list --id $id --accept-source-agreements --exact 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  OK $name (installed)" -ForegroundColor Green; $script:installed += $name; $script:installedCount++; return $true }
    winget install --id $id --accept-source-agreements --accept-package-agreements -h $extra 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  OK $name" -ForegroundColor Green; $script:installed += $name; $script:installedCount++; return $true }
    Write-Host "  FAIL $name" -ForegroundColor Red; $script:failed += $name; $script:failedCount++; return $false
}
function Install-Scoop($name, $pkg) {
    if (-not $pkg) { Write-Host "  SKIP $name (no scoop pkg)" -ForegroundColor Gray; return $false }
    # validate name exists in a bucket before install (avoids aborting batch)
    $valid = scoop search $pkg 2>$null
    if ($valid -notmatch [regex]::Escape($pkg)) { Write-Host "  SKIP $name (scoop pkg '$pkg' not found)" -ForegroundColor Yellow; return $false }
    scoop install $pkg 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  OK $name" -ForegroundColor Green; $script:installed += $name; $script:installedCount++; return $true }
    Write-Host "  FAIL $name" -ForegroundColor Red; $script:failed += $name; $script:failedCount++; return $false
}

# pinned Python (official installer, version-locked) - Scoop only ships latest
function Install-PythonPinned($a) {
    $tmp = Join-Path $env:TEMP ([IO.Path]::GetFileName($a.U))
    Write-Host "  ... downloading $($a.Name) ..." -ForegroundColor Yellow
    try { Invoke-WebRequest -Uri $a.U -OutFile $tmp -UseBasicParsing -ErrorAction Stop }
    catch { Write-Host "  FAIL download $($a.Name): $_" -ForegroundColor Red; $script:failed += $a.Name; $script:failedCount++; return }
    $target = Join-Path $InstallRoot $a.Target
    $args = "/quiet InstallAllUsers=0 TargetDir=`"$target`" Include_pip=1 PrependPath=0 Include_launcher=0 Include_test=0"
    Write-Host "  ... installing $($a.Name) -> $target" -ForegroundColor Yellow
    Start-Process -FilePath $tmp -ArgumentList $args -Wait -ErrorAction SilentlyContinue
    if ($a.AddPath) { Add-UserPath $target; Add-UserPath (Join-Path $target "Scripts") }
    Write-Host "  OK $($a.Name)" -ForegroundColor Green
    $script:installed += $a.Name; $script:installedCount++
}

# PyCharm Professional (version-locked, official installer; needs legit license)
function Install-PyCharmPro($a) {
    $tmp = Join-Path $env:TEMP ([IO.Path]::GetFileName($a.U))
    Write-Host "  ... downloading $($a.Name) ..." -ForegroundColor Yellow
    try { Invoke-WebRequest -Uri $a.U -OutFile $tmp -UseBasicParsing -ErrorAction Stop }
    catch { Write-Host "  FAIL download $($a.Name): $_" -ForegroundColor Red; $script:failed += $a.Name; $script:failedCount++; return }
    Write-Host "  ... running installer (silent). Activate with your own JetBrains license later." -ForegroundColor Yellow
    Start-Process -FilePath $tmp -ArgumentList "/S" -Wait -ErrorAction SilentlyContinue
    Write-Host "  OK $($a.Name) (needs legit license)" -ForegroundColor Green
    $script:installed += $a.Name; $script:installedCount++
}

# package table: Name, WingetId, Scoop, DirectUrl, Special
$apps = @(
    @{Name="Git";                    W="Git.Git";                           S="git";                          U="";        Special=""},
    @{Name="Python 3.9.13";          W="";                                  S="";                            U="https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe";  Special="PythonPinned"; Target="Python39";  AddPath=$false},
    @{Name="Python 3.10.11";         W="";                                  S="";                            U="https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"; Special="PythonPinned"; Target="Python310"; AddPath=$false},
    @{Name="Python 3.11.9";          W="";                                  S="";                            U="https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe";  Special="PythonPinned"; Target="Python311"; AddPath=$true},
    @{Name="VS Code";                W="Microsoft.VisualStudioCode";        S="vscode";                      U="";        Special=""},
    @{Name="Cursor";                 W="Anysphere.Cursor";                  S="cursor";                      U="https://download.cursor.com/latest/win";
                                                                                                                                Special=""},
    @{Name="PyCharm Pro 2022.3.3";   W="";                                  S="";                            U="https://download.jetbrains.com/python/pycharm-professional-2022.3.3.exe"; Special="PyCharmPro"},
    @{Name="MongoDB";                W="MongoDB.Server";                    S="mongodb";                     U="";        Special=""},
    @{Name="MongoDB Compass";        W="MongoDB.Compass";                   S="mongodb-compass";             U="";        Special=""},
    @{Name="Redis";                  W="Redis.Redis";                       S="redis";                       U="";        Special="Redis"},
    @{Name="Another Redis Desktop";  W="qishibo.AnotherRedisDesktopManager";S="another-redis-desktop-manager";U="";       Special=""},
    @{Name="Navicat Premium";        W="PremiumSoft.NavicatPremium";        S="";                            U="https://download.navicat.com/download/navicat-premium.exe"; Special=""},
    @{Name="Apifox";                 W="Ruihu.Apifox";                      S="apifox";                      U="";        Special=""},
    @{Name="Charles";                W="XK72.Charles";                      S="";                            U="https://www.charlesproxy.com/assets/release/5.2/Charles64.msi"; Special=""},
    @{Name="Typora";                 W="appmakes.Typora";                   S="typora";                      U="";        Special=""},
    @{Name="PixPin";                 W="PixPin.PixPin";                     S="pixpin";                      U="";        Special=""},
    @{Name="Sparkle";                W="xishang0128.Sparkle";               S="sparkle";                     U="";        Special=""},
    @{Name="CC Switch";              W="farion1231.CC-Switch";              S="cc-switch";                   U="";        Special=""},
    @{Name="Baidu Netdisk";          W="Baidu.BaiduNetdisk";                S="baidunetdisk";                U="";        Special=""},
    @{Name="uTools";                 W="Yuanli.uTools";                     S="utools";                      U="";        Special=""},
    @{Name="WeChat";                 W="Tencent.WeChat";                    S="wechat";                      U="";        Special=""},
    @{Name="Sunlogin";               W="XPDDRBQ2D1N7NJ";                    S="";                            U="https://down.sunlogin.oray.com/sunlogin/windows/SunLoginClient.exe"; Special=""},
    @{Name="Proxifier";              W="VentoByte.Proxifier";               S="";                            U="https://www.proxifier.com/download/ProxifierSetup.exe"; Special=""},
    @{Name="Clash Verge Rev";        W="ClashVergeRev.ClashVergeRev";       S="clash-verge-rev";             U="";        Special=""},
    @{Name="SpaceSniffer";           W="UderzoSoftware.SpaceSniffer";       S="spacesniffer";                U="";        Special=""}
)

foreach ($a in $apps) {
    if ($a.Special -eq "Redis") {
        # Redis: install binary, config handled by configure-services.ps1
        Write-Host "[DB] $($a.Name)" -ForegroundColor Magenta
        if ($pm -eq "winget") { Install-Winget $a.Name $a.W } else { Install-Scoop $a.Name $a.S }
        continue
    }
    if ($a.Special -eq "PythonPinned") { Install-PythonPinned $a; continue }
    if ($a.Special -eq "PyCharmPro")   { Install-PyCharmPro $a;   continue }
    Write-Host "  ... $($a.Name)" -ForegroundColor Yellow
    if ($pm -eq "winget") {
        if (-not (Install-Winget $a.Name $a.W)) {
            if ($a.U) { Invoke-Direct $a.Name $a.U } else { Write-Host "  MANUAL $($a.Name)" -ForegroundColor Yellow }
        }
    } else {
        if (-not (Install-Scoop $a.Name $a.S)) {
            if ($a.U) { Invoke-Direct $a.Name $a.U } else { Write-Host "  MANUAL $($a.Name)" -ForegroundColor Yellow }
        }
    }
}

# NVM (Node version manager)
Write-Host "[Node] NVM" -ForegroundColor Magenta
if ($pm -eq "winget") { Install-Winget "NVM for Windows" "CoreyButler.NVMforWindows" } else { Install-Scoop "NVM for Windows" "nvm" }
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$nvmHome = [Environment]::GetEnvironmentVariable("NVM_HOME","Machine")
if ($nvmHome) { $env:Path = "$nvmHome;$env:Path" }
nvm install lts 2>$null; nvm use lts 2>$null
Write-Host "  OK Node: $(node --version 2>$null)" -ForegroundColor Green

# pip mirror + npm mirror
Write-Host "[mirrors] pip / npm" -ForegroundColor Magenta
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple 2>$null
npm config set registry https://registry.npmmirror.com 2>$null
Write-Host "  OK mirrors set" -ForegroundColor Green

# global npm packages
foreach ($p in @("pnpm","yarn","typescript","ts-node","tsx")) {
    npm install -g $p 2>$null
    Write-Host "  npm -g $p : $(& $p --version 2>$null)" -ForegroundColor $(if ($?) { "Green" } else { "Yellow" })
}

# ---------- database services (MySQL / Redis) ----------
Write-Host "[DB services] configure MySQL + Redis" -ForegroundColor Magenta
$svc = Join-Path $PSScriptRoot "configure-services.ps1"
if (Test-Path $svc) {
    & powershell -ExecutionPolicy Bypass -File $svc
} else {
    Write-Host "  SKIP configure-services.ps1 not found" -ForegroundColor Yellow
}

# ---------- summary ----------
$endTime = Get-Date
$dur = $endTime - $startTime
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Bootstrap Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Success: $installedCount" -ForegroundColor Green
Write-Host "Failed:  $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Green" })
Write-Host "Time: $($dur.TotalMinutes.ToString('0.0')) min" -ForegroundColor Cyan
if ($failedCount -gt 0) {
    Write-Host "Failed:" -ForegroundColor Red
    foreach ($f in $failed) { Write-Host "  - $f" -ForegroundColor Red }
}
Write-Host ""
Write-Host "Manual steps:" -ForegroundColor Yellow
Write-Host "  1. Docker Desktop: reboot + enable WSL2/Hyper-V (needs admin)" -ForegroundColor Gray
Write-Host "  2. Charles: install SSL cert (Help > SSL Proxying)" -ForegroundColor Gray
Write-Host "  3. Navicat/PyCharm Pro: activate with your license" -ForegroundColor Gray
Write-Host "  4. Sparkle/Proxifier/CC Switch: configure subscriptions" -ForegroundColor Gray
Write-Host "  5. pip deps: pip install scrapy requests httpx aiohttp selenium playwright bs4 lxml pandas" -ForegroundColor Gray
