# Configure MySQL + Redis as local dev services (non-admin friendly)
# ASCII only. Provides: official MySQL ZIP + VC++ runtime fix, Redis MSYS-safe config,
# User PATH, and logon auto-start (HKCU Run key, fallback to Startup folder .bat).
# Called by bootstrap.ps1. Safe to run standalone.

$InstallRoot = "D:\worksoft"
$ErrorActionPreference = "Continue"

# ---------- helpers ----------
function Get-DllVersion($path) {
    if (-not (Test-Path $path)) { return $null }
    try { return [System.Diagnostics.FileVersionInfo]::GetVersionInfo($path).FileVersion } catch { return $null }
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
function Set-AutoStart($name, $target, $args = "") {
    # primary: HKCU Run key
    try {
        $reg = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        $value = if ($args) { "`"$target`" $args" } else { "`"$target`"" }
        New-ItemProperty -Path $reg -Name $name -Value $value -PropertyType String -Force | Out-Null
        Write-Host "    OK auto-start via HKCU Run key: $name" -ForegroundColor Green
        return
    } catch {
        Write-Host "    WARN HKCU Run key blocked ($_), falling back to Startup folder" -ForegroundColor Yellow
    }
    # fallback: Startup folder (.bat)
    $startup = [Environment]::GetFolderPath("Startup")
    $bat = Join-Path $startup "$name.bat"
    $content = "@echo off`r`nstart `"`" /min `"$target`" $args`r`n"
    Set-Content -Path $bat -Value $content -Encoding ASCII
    Write-Host "    OK auto-start via Startup folder: $bat" -ForegroundColor Green
}

# ============================================================
# MySQL
# ============================================================
function Setup-MySql {
    Write-Host "[MySQL] configuring ..." -ForegroundColor Magenta
    $ver = "9.7.1"
    $zipUrl = "https://cdn.mysql.com/Downloads/MySQL-9.7/mysql-$ver-winx64.zip"
    $mysqlDir = Join-Path $InstallRoot "MySQL\mysql-$ver-winx64"
    $mysqld = Join-Path $mysqlDir "bin\mysqld.exe"

    # locate existing mysqld (winget may have installed elsewhere)
    if (-not (Test-Path $mysqld)) {
        $found = Get-ChildItem "$InstallRoot\MySQL" -Recurse -Filter mysqld.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $mysqld = $found.FullName; $mysqlDir = Split-Path (Split-Path $mysqld) }
    }

    # download + extract if missing
    if (-not (Test-Path $mysqld)) {
        Write-Host "  ... downloading MySQL $ver (official ZIP) ..." -ForegroundColor Yellow
        $zip = Join-Path $env:TEMP "mysql-$ver-winx64.zip"
        Invoke-WebRequest -Uri $zipUrl -OutFile $zip -UseBasicParsing
        Write-Host "  ... extracting ..." -ForegroundColor Yellow
        Expand-Archive -Path $zip -DestinationPath (Join-Path $InstallRoot "MySQL") -Force
    }
    if (-not (Test-Path $mysqld)) { Write-Host "  FAIL mysqld not found after extract" -ForegroundColor Red; return }

    # ---- VC++ runtime fix (MSVCP140 crash on missing VS2022 runtime) ----
    $sysMsvcp = Join-Path $env:SystemRoot "System32\msvcp140.dll"
    $sysVer = Get-DllVersion $sysMsvcp
    $needFix = $false
    if ($sysVer) {
        $maj = [int]($sysVer.Split('.')[0]); $min = [int]($sysVer.Split('.')[1])
        if (($maj -lt 14) -or ($maj -eq 14 -and $min -lt 30)) { $needFix = $true }
    } else { $needFix = $true }

    if ($needFix) {
        Write-Host "  ... system VC++ runtime too old ($sysVer); locating VS2022 CRT locally ..." -ForegroundColor Yellow
        $cand = $null
        Get-ChildItem $InstallRoot -Recurse -Filter msvcp140.dll -ErrorAction SilentlyContinue | ForEach-Object {
            $v = Get-DllVersion $_.FullName
            if ($v) {
                $mj = [int]($v.Split('.')[0]); $mn = [int]($v.Split('.')[1])
                if (($mj -ge 14 -and $mn -ge 30) -and -not $cand) { $cand = $_.DirectoryName }
            }
        }
        if ($cand) {
            $bin = Join-Path $mysqlDir "bin"
            foreach ($d in @("vcruntime140.dll","vcruntime140_1.dll","msvcp140.dll","msvcp140_1.dll","concrt140.dll")) {
                $s = Join-Path $cand $d
                if (Test-Path $s) { Copy-Item $s (Join-Path $bin $d) -Force }
            }
            Write-Host "    OK copied VS2022 CRT from $cand" -ForegroundColor Green
        } else {
            Write-Host "    WARN no local VS2022 runtime found. Install vc_redist.x64.exe (VS2022) or copy the 5 CRT DLLs into $bin" -ForegroundColor Red
        }
    } else { Write-Host "  OK system VC++ runtime is recent ($sysVer)" -ForegroundColor Green }

    # ---- my.ini ----
    $ini = Join-Path $mysqlDir "my.ini"
    $dataDir = Join-Path $mysqlDir "data"
    $iniText = @"
[mysqld]
basedir="$mysqlDir"
datadir="$dataDir"
port=3306
character-set-server=utf8mb4
default_authentication_plugin=mysql_native_password
"@
    Set-Content -Path $ini -Value $iniText -Encoding UTF8

    # ---- initialize (idempotent) ----
    if (-not (Test-Path (Join-Path $dataDir "mysql"))) {
        Write-Host "  ... initializing data directory ..." -ForegroundColor Yellow
        & $mysqld --initialize-insecure --console 2>&1 | Out-Null
    } else { Write-Host "  skip (data already initialized)" -ForegroundColor Gray }

    # ---- PATH ----
    Add-UserPath (Join-Path $mysqlDir "bin")

    # ---- start/stop scripts ----
    $startBat = Join-Path $InstallRoot "MySQL\start-mysql.bat"
    $stopBat  = Join-Path $InstallRoot "MySQL\stop-mysql.bat"
    Set-Content -Path $startBat -Value "@echo off`r`nstart `"`" /min `"$mysqld`" --console`r`n" -Encoding ASCII
    Set-Content -Path $stopBat  -Value "@echo off`r`n`"$(Join-Path $mysqlDir 'bin\mysqladmin.exe')`" -u root shutdown`r`n" -Encoding ASCII

    # ---- launch now ----
    Start-Process -FilePath $mysqld -ArgumentList "--console" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    # ---- auto-start ----
    Set-AutoStart "MySQL_AutoStart" $mysqld "--console"

    Write-Host "  MySQL $ver configured. root has empty password (set one for networked machines)." -ForegroundColor Green
}

# ============================================================
# Redis
# ============================================================
function Setup-Redis {
    Write-Host "[Redis] configuring ..." -ForegroundColor Magenta
    $redisHome = Join-Path $InstallRoot "Redis"
    $rdir = Join-Path $InstallRoot "scoop\apps\redis\current"
    if (-not (Test-Path (Join-Path $rdir "redis-server.exe"))) {
        $rdir = (Get-ChildItem (Join-Path $InstallRoot "scoop\apps\redis") -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
    }
    $server = Join-Path $rdir "redis-server.exe"
    if (-not (Test-Path $server)) {
        # winget install path
        $w = Get-ChildItem "C:\Program Files\Redis","$InstallRoot\Redis" -Recurse -Filter redis-server.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($w) { $server = $w.FullName; $rdir = Split-Path $server }
    }
    if (-not (Test-Path $server)) { Write-Host "  FAIL redis-server.exe not found (install Redis first)" -ForegroundColor Red; return }
    Write-Host "  using redis-server: $server" -ForegroundColor Gray

    New-Item -ItemType Directory -Force -Path $redisHome | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $redisHome "data") | Out-Null

    # relative-path config (MSYS-safe: launcher cd's into redisHome first)
    $conf = Join-Path $redisHome "redis.conf"
    $confText = @"
port 6379
bind 127.0.0.1
protected-mode yes
daemonize no
logfile redis.log
dir data
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
maxmemory 256mb
maxmemory-policy allkeys-lru
timeout 0
tcp-keepalive 300
"@
    Set-Content -Path $conf -Value $confText -Encoding UTF8

    # start/stop scripts (cd + relative path avoids MSYS path conversion)
    $startBat = Join-Path $redisHome "start-redis.bat"
    $stopBat  = Join-Path $redisHome "stop-redis.bat"
    Set-Content -Path $startBat -Value "@echo off`r`ncd /d `"$redisHome`"`r`nstart `"`" /min `"$server`" redis.conf`r`n" -Encoding ASCII
    Set-Content -Path $stopBat  -Value "@echo off`r`n`"$(Join-Path $rdir 'redis-cli.exe')`" -p 6379 shutdown save`r`n" -Encoding ASCII

    # launch now
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$redisHome`" && start `"`" /min `"$server`" redis.conf" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    # auto-start (Startup folder .bat copy)
    $startup = [Environment]::GetFolderPath("Startup")
    Copy-Item $startBat (Join-Path $startup "Redis_AutoStart.bat") -Force
    Write-Host "  OK auto-start via Startup folder" -ForegroundColor Green

    Write-Host "  Redis configured (127.0.0.1:6379). No password by default; add requirepass for networked use." -ForegroundColor Green
}

# ---------- run ----------
Setup-MySql
Setup-Redis

Write-Host ""
Write-Host "Done. Verify: mysql -u root  /  redis-cli ping" -ForegroundColor Cyan
