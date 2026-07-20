---
name: "windows-dev-bootstrap"
description: "Initialize a Windows dev environment: install software in the background, configure Node.js/Python, databases and service auto-start. Legal software only, no cracks/activation. Adaptive winget + Scoop, works in non-admin/offline setups."
---

# Windows Dev Bootstrap (async mode, adaptive)

One-shot setup of a new PC's dev environment. Based on **winget / Scoop** + NVM + pip, covering IDEs, databases, sniffing tools, and productivity apps.

**Core principle: run asynchronously, never block the session.**

> WARNING (security audit): This skill has REMOVED the original JetBrains activation/crack scripts (micool_config etc. that edit hosts and drop cracked files into system dirs). Only the legitimate install flow remains.
> For commercial IDEs like PyCharm Professional, use the official installer + your own licensed copy (Community is free). No crack/activation is ever installed.

---

## Key optimizations vs the original (from real-world testing)

| Pain point (original) | Optimization |
|---|---|
| winget fails offline / no Store / non-admin (missing Microsoft.VCLibs.140.00 >=14.0.33519.0, no public offline source) | Added **Scoop as primary fallback**: pure user-mode, no VCLibs/Store/admin, installs to D:\worksoft |
| Scoop aborts the whole `scoop install` when one package fails | **Validate package names first**, then install in groups/singly; one failure is logged, not fatal |
| MySQL 9.x `mysqld --initialize` crashes (0xC0000005 / MSVCP140) on machines missing VS2022 runtime | Provide **official ZIP + copy VS2022 CRT** (drop the 5 DLLs next to mysqld) fallback; no system service, use logon auto-start |
| Redis (MSYS build) mangles drive-letter paths in config | Launcher `cd`s into the config dir and uses **relative paths** in config, avoiding MSYS path conversion |
| Auto-start relies on schtasks/COM, often blocked in sandboxes | Prefer **HKCU Run key**; fall back to **Startup folder .bat** (both need no admin) |
| PATH changes need admin | Always write to **User PATH** (current-user scope) |
| PyCharm defaults to Community; Pro needs a crack | Guide to **official Professional installer + legit license**, never touch cracks |
| Wrong/missing winget package name aborts the batch | check-env.ps1 / bootstrap.ps1 validate names and skip already-installed idempotently |

---

## Async workflow (3 phases)

### Phase 1: Build software list & collect config

Based on the user role (default: crawler engineer) and preferences, confirm what to install.

- Read `references/packages.md` for the default list (category + winget id + Scoop name + direct URL)
- Show to the user for confirmation; allow add/remove ("drop Navicat", "add Postman")
- Collect Git username/email once

Output: Markdown table of the list + category summary.

### Phase 2: Environment check (sync, fast)

Run `scripts/check-env.ps1` to detect installed software, missing items, and **recommend a package manager**:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/check-env.ps1"
```

- Detects winget availability, admin rights, Scoop presence
- Outputs missing list + recommended approach (winget / Scoop / mixed)
- After confirmation, enter async install
- Reminder: MySQL, Docker full service need admin; non-admin MySQL uses official ZIP + logon auto-start, Docker may fail (script marks it)

### Phase 3: Async batch install

Core change: do not wait phase-by-phase; push all work via subtasks/background processes.

#### 3a. Build install plan

From the confirmed list, generate `install-plan.json` (temp file) containing:
- source per app: `winget` / `scoop` / `direct` (official download)
- package name / id / direct URL
- mirror config, Git config

#### 3b. Launch async install

Use a sub-agent to run the install script and return control immediately:

```
You are the Windows install executor. Steps:
1. Run: powershell -ExecutionPolicy Bypass -File "scripts/bootstrap.ps1"
2. Script auto-selects package manager (winget if available+admin, else Scoop)
3. All installs are idempotent (skip if present); one failure does not stop the rest
4. DB services (MySQL/Redis) are configured and set to logon auto-start as needed
5. Script prints a summary at the end (success/failed/duration)
6. After completion, give a concise summary of what installed, what failed, and manual steps
```

#### 3c. Report status (async)

After launching the sub-agent, immediately tell the user:

```
Install task started in the background.

Status: running, including:
- package manager installs (winget or Scoop)
- database service config (MySQL / Redis)
- npm global packages, pip mirrors
- Git config

You can keep working; I will notify you when done.
```

#### 3d. Post-install

When the sub-agent finishes, the user is notified. Run a quick verification:

```powershell
$tools = @("git","python","node","npm","pnpm","mysql","redis-cli","docker")
foreach ($t in $tools) {
    $v = & $t --version 2>$null
    if ($v) { Write-Host "OK $t $v" } else { Write-Host "MISSING $t" }
}
```

---

## Install order (inside bootstrap.ps1)

1. Core: Git, Python 3.9 / 3.10 / 3.11 (official installers, version-locked; 3.11 -> User PATH), pip mirror
2. IDEs: VS Code, Cursor, PyCharm Professional 2022.3.3 (official installer, needs legit license)
3. Databases: MySQL, MongoDB, Redis, Navicat (official trial)
4. Debug: Apifox, Charles (official)
5. Utils: Typora, PixPin, Sparkle, WeChat, Baidu Netdisk, uTools, CC Switch, Proxifier, Clash Verge, SpaceSniffer
6. Container: Docker Desktop (needs admin/WSL2)
7. Node: NVM -> Node LTS -> npm mirror -> global packages

---

## Install principles

- Idempotent: detect then install, skip if present
- Silent: winget `-h`, Scoop default
- Error isolation: one failure does not stop the rest; Scoop must validate names then group-install
- Async: agent does not wait for install, subtask reports
- User PATH first: avoid admin

---

## Known pitfalls & fixes (from real testing)

### A. winget fails offline / non-admin
- Symptom: `winget install` reports missing `Microsoft.VCLibs.140.00`.
- Fix: use **Scoop**. bootstrap.ps1 falls back automatically; or manually:
  ```powershell
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  irm get.scoop.sh | iex
  scoop config SCOOP_ROOT D:\worksoft\scoop
  ```

### B. MySQL init crash (0xC0000005 / MSVCP140)
- Symptom: `mysqld --initialize` access violation; event log blames `MSVCP140.dll`.
- Root cause: only VS2017 runtime present; MySQL 9.x needs VS2022 (14.3x+).
- Fix (non-admin): copy the 5 CRT DLLs (vcruntime140 / vcruntime140_1 / msvcp140 / msvcp140_1 / concrt140) from a local dir that ships a newer runtime (e.g. some app's `msvcp140.dll` 14.3x+) into `mysql\bin`; Windows loads the co-located DLL first.
- See `Setup-MySql` in `scripts/configure-services.ps1`.

### C. Redis config path mangled by MSYS
- Symptom: `D:\worksoft\...\redis.conf` treated as relative; `/d/...` not found; `D:/...` still crashes.
- Fix: launcher `cd /d D:\worksoft\Redis` then `start redis-server redis.conf`; config uses `dir data` / `logfile redis.log` (relative).
- See `Setup-Redis` in `scripts/configure-services.ps1` and `D:\worksoft\Redis\start-redis.bat`.

### D. Auto-start blocked by sandbox
- Symptom: `schtasks` / WScript.Shell COM / new `HKCU\...\Run` value writes are denied.
- Fix: prefer HKCU Run key; if blocked, drop a `.bat` into the Startup folder `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`.

### E. .bat / .ps1 encoding
- `.bat` MUST be pure ASCII (GBK cmd misreads UTF-8 and breaks the script).
- `.ps1` should be UTF-8 **with BOM**, or ASCII, to avoid mojibake on GBK systems.

---

## Notes

- Admin: MySQL service, Docker full install need admin; non-admin MySQL uses official ZIP + logon auto-start, Docker may fail (mark it)
- Docker: needs WSL2/Hyper-V, reboot after first install
- MongoDB: Scoop/winget install Server (858MB+); Compass GUI is `MongoDB.Compass`; registering the service needs admin
- Navicat / Cursor / Sunlogin / PixPin / Sparkle / CC Switch / Proxifier: often not in main Scoop buckets; use official direct URLs in `references/packages.md`
- Charles: install SSL cert manually to sniff HTTPS
- PyCharm Professional: official installer + legit license, no cracks
- Terminal restart: NVM/Node need a new terminal to take effect

---

## Host compatibility

- Windows 10 build 1809+ or Windows 11
- winget recommended (install App Installer from Store); Scoop auto-used when winget missing
- Some software (Docker full service) needs Pro/Enterprise + admin
