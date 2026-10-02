<div align="center">

**English | [简体中文](README_ZH.md)**

# ZenX Bridge Skill

**Real browser control skill for local AI agents with privacy minimization and tab safety**

[![Agent Skill](https://img.shields.io/badge/Agent-Skill-black.svg)](skill/SKILL.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#quick-start)
[![Version](https://img.shields.io/badge/Version-v1.1.0-green.svg)](CHANGELOG.md)
[![bsk](https://img.shields.io/badge/bsk-0.4.0%2B%20fork-orange.svg)](https://github.com/916938/zenx-bridge)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Version Compatibility](#version-compatibility)
- [Quick Start](#quick-start)
- [Installation Guide](#installation-guide)
  - [Windows Installation](#windows-installation-codebuddy--workbuddy--claude-code--codex)
  - [Linux/macOS Installation](#linuxmacos-installation-codebuddy--workbuddy--claude-code--codex)
  - [Docker Deployment](#docker-containerized-deployment)
- [Multi-Environment Support](#multi-environment-support)
- [Usage Examples](#usage-examples)
- [Privacy & Security](#privacy--security)
- [Project Structure](#project-structure)
- [Verification & Testing](#verification--testing)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Introduction

ZenX Bridge Skill is a standalone Agent Skill that controls users' **real, authenticated browsers** through the local **BrowserSkill daemon**.

As long as an Agent can read Agent Skill instructions and execute local shell commands, it can use the core workflow. This repository additionally provides OpenAI/Codex metadata, but core protocol and operation instructions do not depend on any specific Agent product.

**Aligned bsk version**: CLI and extension **0.4.0** (daemon protocol **1.3**). Since 0.2.2 the CLI, extension and DSH plugin share one semver — upgrade all three together, because a mismatch fails with exit code 5.

> ⚠️ **This skill requires the fork build** — [`916938/zenx-bridge`](https://github.com/916938/zenx-bridge), not upstream
> [`Tencent/BrowserSkill`](https://github.com/Tencent/BrowserSkill). Upstream releases do **not** work: several commands this
> skill documents exist only in the fork (`browsers close`, `--browser-id` tab management, `tab observe`, `invoke`,
> `templates`, `completion`). The fork keeps its own version line, always numbered above the upstream release it last synced
> (upstream 0.3.0 → fork 0.4.0), so the version alone tells you which distribution you are running.

### ⚠️ Project Origin & Disclaimer

> **Important:** This project is a **community-driven derivative work**, not an official product of Tencent or any affiliated organization.

**Project Lineage:**

```
Tencent/BrowserSkill (Official)
        │
        ├──► 916938/zenx-bridge (Community Fork & Enhanced Version)
        │           │
        │           └──► 916938/zenx-bridge-skill (This Repository - Pro Edition)
        │
        └──► Other community forks and derivatives
```

**Relationship to Upstream Projects:**

| Repository | Role | Maintainer | License |
|------------|------|-----------|---------|
| [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | **Original/Upstream** | Tencent (Official) | MIT |
| [916938/zenx-bridge](https://github.com/916938/zenx-bridge) | **Enhanced Base** | Community (916938) | MIT |
| **916938/zenx-bridge-skill** (this repo) | **Pro Edition** | Community (916938) | MIT |

**Key Distinctions from Official Version:**
- This is an **unofficial, community-maintained enhancement** of the original BrowserSkill
- Adds multi-platform installation scripts (Windows/Linux/macOS)
- Provides Docker deployment solutions
- Supports multiple AI Agent environments (CodeBuddy/Claude Code/WorkBuddy/Codex)
- Includes comprehensive documentation and layered architecture
- May include features not present in the upstream official version

**Compliance Notice:**
- ✅ Fully complies with [MIT License](LICENSE) terms
- ✅ Proper attribution to upstream projects maintained
- ❌ Not endorsed, sponsored, or officially associated with Tencent
- ⚠️ Users should review upstream [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) for official releases and security updates

For the latest stable base version with Windows compatibility fixes and multi-browser support, see [browserskill-new](https://github.com/916938/zenx-bridge).

### Use Cases

- Reading websites where users are already logged in
- Searching, clicking, and filling forms in existing tabs
- Saving page screenshots or PDFs
- Troubleshooting when pages don't change after clicks, background tabs, or popup blocking

### Architecture Overview

```
Local AI Agent (CodeBuddy / Claude Code / WorkBuddy / Codex)
       │
       ▼
   bsk CLI ──► 127.0.0.1:52800 daemon (WebSocket)
                    │
                    ▼
          Browser Extension + Real Chromium Tabs
```

> **Note:** This project is NOT a search engine and does not contain browser drivers. It depends on **BrowserSkill daemon** and browser extensions, supplementing cross-Agent workflow constraints on top of the original skill.

---

## Features

| Feature | Description |
|---------|-------------|
| **Session Lifecycle** | `bsk session start` / `stop` — one session per task; the 5-minute idle timeout is a backstop, not cleanup |
| **Semantic Observation** | `bsk observe` returns the VOM semantic view with fresh `@e` refs and is the default first observation; `--probe-hover` uncovers CSS hover menus |
| **Tab Borrow/Return** | `bsk tab borrow` / `bsk tab return` safely borrows user tabs and returns them as soon as the step is done |
| **Multi-Browser & Instance Routing** | `bsk browsers` lists instances; `--browser-id <instance_id>` routes exactly (a smart label is only an editable alias and may be duplicated) |
| **Rich Interaction Commands** | `click`, `hover`, `fill`, `select`, `press`, `scroll-to`, `wheel`, `focus`, `blur` |
| **File Upload & Download** | `bsk upload` (input mode or `--mode drop`) and `bsk download` stage files through the daemon, never through browser-internal paths |
| **Record & Replay** | `bsk record` captures a user's actions; `replay.py` replays a trace by semantic target (always `--dry-run` first) |
| **Debugging Evidence** | `network` / `console` read requests and logs with cursor pagination; `screenshot` (incl. `--full-page`) and `get-html` |
| **Human Intervention Request** | `bsk request-help` asks the user to handle CAPTCHA, login, OTP, or payment confirmation |
| **Smart Snapshot & Waiting** | `snapshot.py --auto` picks compact vs. file output; `wait_for.py` polls URL, title, or visible text |
| **Health & Degradation** | `doctor.py` (no-side-effect check), `health_checker.py` (session health report), `fallback_chain.py` (level-by-level fallback) |
| **Read-Only User Tab Observation** | `bsk tab observe --browser-id` reads visible text only: no injection, no CDP, no access to forms or storage (fork build) |
| **Close a Browser Instance** | `bsk browsers close --browser-id <id> --confirm` — only when the user explicitly asks for that instance to be closed (fork build) |
| **Cross-Platform Helpers** | Windows (PowerShell) and Linux/macOS (Bash) helpers plus zero-dependency Python helpers |
| **Privacy Minimization** | Limits reading of cookies, auth headers, tokens, password fields, browser storage, and unrelated private content |
| **Layered Documentation** | `SKILL.md` → `protocol.md` → `operations.md` → capability docs (long screenshot / wheel / scroll-to / audit / sandbox / user tabs) |

---

## Version Compatibility

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| bsk CLI | 0.1.0 | **0.4.0** (fork build) | Below 0.2.0 the helpers fall back to legacy (typed subcommand) mode |
| Browser extension | 0.1.0 | **0.4.0** (fork build, must match the CLI) | A CLI/extension mismatch surfaces as exit code 5 |
| Daemon protocol | 1.2 | **1.3** | `request-help` needs 1.3; `tab borrow --timeout` needs 1.2 |
| Python | 3.8+ | 3.12+ | Helpers only; no third-party dependencies |
| Node.js / pnpm | 18+ / 9.x | 20 LTS / 10.17.0 | Only needed to build the extension from source |

Capabilities ship in **three tiers**, and both this README and `skill/SKILL.md` label them:

| Tier | Meaning | Examples |
|------|---------|----------|
| **0.2.3** | Released baseline (2026-09-08) | `observe`, `snapshot`, borrow/return, `request-help`, `record`, `network` / `console`, `upload` / `download`, `emulate`, `templates` |
| **0.2.4+** | Merged after the 0.2.3 tag; needs a build newer than 2026-09-08 | `screenshot --full-page`, `wheel`, `scroll-to`, `focus` / `blur`, `session start --name` with operation audit |
| **Fork build** | `916938/zenx-bridge` only, absent from upstream releases | `tab list\|create\|select --browser-id`, `tab observe`, `browsers close`, `invoke`, `templates`, `completion`, `since last_action`, profile account id, smart labels |

> The fork's **0.4.0** build already contains the 0.2.3 baseline and the 0.2.4+ tier, so installing the fork gets you all
> three tiers at once — except that upstream's remote/server mode, which the fork carries but does **not** support, is never
> a capability here. For anything in the 0.2.4+/fork tiers on an older build, confirm with `bsk <command> --help` before
> relying on it, and continue with what the installed build supports when it is missing.

---

## Quick Start

### 1. Install BrowserSkill (bsk CLI + daemon)

> You need to install the local daemon and browser extension before using this skill. Current aligned version: **0.2.3**

**macOS / Linux:**
```bash
# Upstream Tencent/BrowserSkill
curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh

# Or the fork (recommended): bsk invoke, user-tab commands and other Pro dependencies live there
curl -fsSL https://raw.githubusercontent.com/916938/zenx-bridge/main/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex

# Fork build (recommended)
irm https://raw.githubusercontent.com/916938/zenx-bridge/main/install.ps1 | iex
```

**Or via Cargo:**
```bash
cargo install bsk-cli
```

Verify afterwards: `bsk --version` — the CLI and extension versions must match, otherwise every command fails with exit code 5.

### 2. Install Browser Extension

Install from [Chrome Web Store](https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi), or build from source:

```bash
cd <browser-skill-repo>
pnpm install && pnpm ext:build  # Output: apps/extension/dist/chrome-mv3
```

Then load unpacked extension in Chrome (`chrome://extensions` → Developer mode → Load unpacked).

> For detailed build steps, see [operations.md - Building the extension from source](skill/references/operations.md#building-the-extension-from-source)

Confirm daemon, port, and extension connectivity with `bsk doctor`.

### 3. Install This Skill

**Automatic (recommended):** `bsk install-skill` writes the skill into the agent harnesses it detects:

```bash
bsk install-skill --list             # show available harnesses
bsk install-skill --all              # install everywhere
bsk install-skill --source <path>    # install a custom SKILL.md (suspends skill auto-update)
```

**Manual:** copy the `skill/` directory from this repository to your Agent's skills directory:

```text
<agent-skills-directory>/
└── zenx-bridge-skill/
    ├── SKILL.md          # Core Agent instructions
    ├── scripts/          # Python/Bash/PowerShell helpers
    ├── examples/         # Workflow examples
    └── references/       # Protocol and operation docs
```

### 4. Self-Check Verification

**Windows:**
```powershell
py -3 <your-path>\zenx-bridge-skill\scripts\doctor.py --wait-connected 20
```

**Linux / macOS:**
```bash
python3 <your-path>/zenx-bridge-skill/scripts/doctor.py --wait-connected 20
```

Expected output:
```json
{
  "ready": true,
  "reason": "All checks passed",
  "checks": [
    {"name": "daemon_running", "status": "passed"},
    {"name": "port_52800_listening", "status": "passed"},
    {"name": "extension_connected", "status": "passed"}
  ]
}
```

### 5. Start Using

In your Agent dialog, type:

```text
Use $zenx-bridge-skill to check my currently opened web page.
```

```text
Use $zenx-bridge-skill to search for OpenAI on my Zhihu page.
```

```text
Use $zenx-bridge-skill to take a screenshot of the current page and delete temporary files after completion.
```

---

## Installation Guide

### Windows Installation (CodeBuddy / WorkBuddy / Claude Code / Codex)

#### Method 1: Git Clone + Manual Copy (Recommended)

```powershell
# 1. Clone repository
git clone https://github.com/916938/zenx-bridge-skill.git %TEMP%\bsk-install

# 2. Copy to target path (choose based on your Agent environment)
$target = "$env:USERPROFILE\.codebuddy\skills\zenx-bridge-skill"     # CodeBuddy
# $target = "$env:USERPROFILE\.workbuddy\skills\zenx-bridge-skill"   # WorkBuddy
# $target = "$env:USERPROFILE\.claude\skills\zenx-bridge-skill"      # Claude Code (Skills)
# $target = "$env:USERPROFILE\.claude\commands\zenx-bridge-skill"    # Claude Code (Commands)
# $target = "$env:USERPROFILE\.codex\skills\zenx-bridge-skill"        # Codex

New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item "%TEMP%\bsk-install\skill\*" -Destination $target -Recurse -Force

# 3. Clean up and verify
Remove-Item -Recurse -Force %TEMP%\bsk-install
Test-Path "$target\SKILL.md"
```

#### Method 2: PowerShell One-Click Script (Automated)

```powershell
# Download and run directly
irm https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.ps1 | iex

# Or save then run (recommended for code review)
irm https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.ps1 -OutFile install.ps1
.\install.ps1 -Branch main

# Force overwrite existing installation
.\install.ps1 -Branch main -Force
```

**Script Features:**
- ✅ Auto-detect Agent environment (CodeBuddy / WorkBuddy / Claude Code / Codex)
- ✅ Force overwrite with backup support
- ✅ Post-installation verification
- ✅ Color-coded output and error messages

#### Method 3: Manual ZIP Download

1. Visit https://github.com/916938/zenx-bridge-skill
2. Click **Code** → **Download ZIP**
3. Extract and copy `skill/` directory contents to target path

---

### Linux/macOS Installation (CodeBuddy / WorkBuddy / Claude Code / Codex)

#### Prerequisites

```bash
# Check required tools
git --version && python3 --version && curl --version

# If dependencies are missing, install by system:
# Ubuntu/Debian: sudo apt update && sudo apt install -y git python3 curl
# macOS: brew install git python3 curl
# Fedora: sudo dnf install -y git python3 curl
# Arch: sudo pacman -S git python3 curl
```

#### Method 1: Git Clone + Manual Copy (Recommended)

```bash
# 1. Clone repository
TMPDIR=$(mktemp -d)
git clone https://github.com/916938/zenx-bridge-skill.git "$TMPDIR/bsk"

# 2. Choose target path (based on your Agent environment)
TARGET="$HOME/.codebuddy/skills/zenx-bridge-skill"           # CodeBuddy
# TARGET="$HOME/.workbuddy/skills/zenx-bridge-skill"         # WorkBuddy
# TARGET="$HOME/.claude/skills/zenx-bridge-skill"            # Claude Code (Skills)
# TARGET="$HOME/.claude/commands/zenx-bridge-skill"          # Claude Code (Commands)
# TARGET="$HOME/.codex/skills/zenx-bridge-skill"             # Codex

# 3. Copy files
mkdir -p "$(dirname "$TARGET")"
cp -r "$TMPDIR/bsk/skill/." "$TARGET"

# 4. Clean up and verify
rm -rf "$TMPDIR"
test -f "$TARGET/SKILL.md" && echo "✅ Installation successful!"
```

#### Method 2: Bash One-Click Script (Automated)

```bash
# Option A: Execute directly
curl -fsSL https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.sh | bash

# Option B: Download then execute (recommended)
curl -fsSL https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.sh -o install.sh
chmod +x install.sh
./install.sh --branch main

# Advanced options
./install.sh --force                          # Force overwrite
./install.sh --dry-run                        # Dry run (no actual changes)
./install.sh --target-path "/custom/path"     # Custom path
./install.sh -v                               # Verbose output
```

#### Method 3: Manual ZIP Download

```bash
# 1. Download and extract
cd ~/Downloads
unzip zenx-bridge-skill-main.zip -d /tmp/bsk-install

# 2. Copy files
ZIP_EXTRACT="/tmp/bsk-install/zenx-bridge-skill-main"
TARGET="$HOME/.codebuddy/skills/zenx-bridge-skill"
mkdir -p "$(dirname "$TARGET")"
cp -r "$ZIP_EXTRACT/skill/." "$TARGET"

# 3. Verify
test -f "$TARGET/SKILL.md" && echo "✅ Installation successful!"
```

---

### Docker Containerized Deployment

Suitable for CI/CD, isolated environments, and unified deployment scenarios.

#### Prerequisites

```bash
docker --version        # Docker Engine 20.10+
docker compose version  # Docker Compose V2+
```

#### Method 1: Single Container Quick Start (Recommended for Beginners)

```bash
# 1. Build image
git clone https://github.com/916938/zenx-bridge-skill.git
cd zenx-bridge-skill
docker build -t zenx-bridge-skill:latest .

# 2. Run self-check (requires connection to host's bsk daemon)
docker run --rm \
  --network host \
  -v ~/.bsk:/app/.bsk:ro \
  zenx-bridge-skill:latest python3 skill/scripts/doctor.py --wait-connected 20

# 3. Execute snapshot example
docker run --rm --network host \
  zenx-bridge-skill:latest python3 skill/scripts/snapshot.py --session demo --auto
```

**Common Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--network host` | Use host network to access local daemon | Required |
| `-v` | Mount volumes (data persistence) | `-v ./data:/app/data` |
| `-e` | Set environment variables | `-e LOG_LEVEL=DEBUG` |
| `--rm` | Auto-remove container after exit | Recommended for testing |
| `-d` | Run in background (detached mode) | Recommended for production |

#### Method 2: Docker Compose Orchestration (Production Environment)

Complete deployment including **daemon + Chrome + Redis + monitoring**:

```bash
# Start all services
docker compose up -d

# Start core services only (without monitoring)
docker compose up -d bsk-daemon zenx-bridge-skill redis chrome-browser

# Start development environment (source code hot-mounting)
docker compose -f docker-compose.dev.yml up --build -d

# Start complete environment with monitoring
docker compose --profile monitoring up -d

# Access Grafana dashboard
# http://localhost:3000 (default: admin/admin)
```

**Architecture Diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Network (172.28.0.0/16)            │
│                                                             │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────┐   │
│  │ bsk-daemon   │◄──►│zenx-bridge-skill │◄──►│  chrome  │   │
│  │ (WebSocket)  │    │ (Skill + Helpers)│    │(Browser) │   │
│  │ :52800       │    │                 │    │ :9222    │   │
│  └──────┬───────┘    └────────┬────────┘    └──────────┘   │
│         │                     │                              │
│         ▼                     ▼                              │
│  ┌──────────┐          ┌─────────────┐                      │
│  │   redis  │          │ monitoring  │ (Grafana, Optional)  │
│  │ :6379    │          │ :3000       │                      │
│  └──────────┘          └─────────────┘                      │
│                                                             │
│  Volumes: data, screenshots, snapshots, chrome-profile, grafana│
└─────────────────────────────────────────────────────────────┘
```

**Custom Configuration (`.env` file):**

```bash
BSK_AUTH_TOKEN=your-secure-token-here
BSK_MAX_SESSIONS=20
CHROME_MODE=headed              # or headless
LOG_LEVEL=INFO                  # DEBUG, INFO, WARN, ERROR
DOCKER_CPUS_LIMIT=2.0
DOCKER_MEMORY_LIMIT=4G
```

#### Method 3: CI/CD Integration

**GitHub Actions Example (`.github/workflows/docker-test.yml`):**

```yaml
name: Docker Integration Tests
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      bsk-daemon:
        image: zenxbridge/bsk-daemon:latest
        ports:
          - 52800:52800
        options: >-
          --health-cmd "curl -f http://localhost:52801/health || exit 1"
          --health-interval 10s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - name: Build & Test
        run: |
          docker build -t zenx-bridge-skill:test .
          docker run --rm --network host zenx-bridge-skill:test \
            python3 -m unittest discover -s tests -v
```

#### Performance Optimization & Security Hardening

**Reduced Image Size:** Multi-stage build implemented in Dockerfile

**Cache Layer Optimization:** Optimized `.dockerignore`

**Production Security Hardening (additional config):**

```yaml
services:
  zenx-bridge-skill:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:size=100M
      - /app/data/screenshots,size=1G
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

**Troubleshooting:**

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Cannot connect to daemon | Incorrect network mode | Use `--network host` |
| Permission denied | Volume mount permission issue | Adjust UID (`user: "1000:1000"`) |
| Chrome won't start | Insufficient shared memory | Increase `shm_size: '2gb'` |
| Container restart loop | Health check failure | View logs `docker compose logs <service>` |

**Image Management:**

```bash
# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t zenx-bridge-skill:latest .

# Push to registry
docker tag zenx-bridge-skill:latest ghcr.io/916938/zenx-bridge-skill:v1.0.0
docker push ghcr.io/916938/zenx-bridge-skill:v1.0.0

# Export/import (offline environments)
docker save -o zenx-bridge-skill.tar zenx-bridge-skill:latest
docker load -i zenx-bridge-skill.tar
```

---

## Multi-Environment Support

This Skill supports **four major AI Agent platforms**: CodeBuddy, WorkBuddy, Claude Code, and Codex.

| Agent Platform | Skills Path | Commands Path | Notes |
|----------------|------------|---------------|-------|
| **CodeBuddy** | `~/.codebuddy/skills/zenx-bridge-skill` | - | Primary supported platform |
| **Claude Code** | `~/.claude/skills/zenx-bridge-skill` | `~/.claude/commands/zenx-bridge-skill` | Dual-mode support (Skills recommended) |
| **WorkBuddy** | `~/.workbuddy/skills/zenx-bridge-skill` | - | Enterprise-grade Agent |
| **Codex** | `~/.codex/skills/zenx-bridge-skill` | - | OpenAI coding assistant |

### Auto-Detection Priority

When using one-click installation scripts, auto-detection order is:
**CodeBuddy > Claude Code > WorkBuddy > Codex**

Override default paths via environment variables or command-line arguments:

```bash
# Linux/macOS
CODEBUDDY_SKILLS_DIR=/custom/path ./install.sh
./install.sh --target-path "$HOME/.my-agent/skills/zenx-bridge-skill"

# Windows
$env:CODEBUDDY_SKILLS_DIR="C:\Custom\Path"
.\install.ps1
```

### Uninstallation

```bash
# Linux/macOS
rm -rf ~/.codebuddy/skills/zenx-bridge-skill

# PowerShell
Remove-Item -Recurse -Force "$env:USERPROFILE\.codebuddy\skills\zenx-bridge-skill"
```

---

## Usage Examples

### Page Snapshots

**Windows:**
```powershell
# Compact mode (suitable for locating elements)
py -3 .\skill\scripts\snapshot.py --session demo --auto
py -3 .\skill\scripts\snapshot.py --session demo --mode compact

# Full mode (write to temp file)
py -3 .\skill\scripts\snapshot.py --session demo --mode file
```

**Linux / macOS:**
```bash
python3 ./skill/scripts/snapshot.py --session demo --auto
python3 ./skill/scripts/snapshot.py --session demo --mode file
```

### Screenshots

**Windows:**
```powershell
py -3 .\skill\scripts\screenshot.py --session demo
# Full-page capture (0.2.4+, 2-minute default deadline)
py -3 .\skill\scripts\screenshot.py --session demo --full-page --out page.png
```

**Linux / macOS:**
```bash
python3 ./skill/scripts/screenshot.py --session demo
python3 ./skill/scripts/screenshot.py --session demo --full-page --out page.png
```

> `--full-page` and `--selector` are mutually exclusive; see [references/long-screenshot.md](skill/references/long-screenshot.md).

### Semantic Observation (preferred first read)

```bash
bsk observe --session demo                 # VOM semantic view with @e refs
bsk observe --session demo --probe-hover   # once, when an expected control is missing and no hover marker points at a trigger (0.2.2+)
bsk scroll-to @e3 --session demo           # reveal one element (0.2.4+)
bsk wheel --delta-y 600 --session demo     # native wheel input (0.2.4+)
```

### Record and Replay

```bash
scripts/record.sh start --purpose "publish an article" --output ./flow.json
SID=$(bsk session start)
python3 scripts/replay.py ./flow.json --session "$SID" --dry-run   # inspect the plan first
python3 scripts/replay.py ./flow.json --session "$SID"             # then execute
bsk session stop "$SID"
```

### Network and Console Evidence

```bash
scripts/network.sh --session "$SID" --limit 20 --json   # next call: --since <cursor>
bsk console --session "$SID"
```

### File Upload and Download (0.2.2+)

```bash
bsk upload @e12 --file ./report.pdf --session "$SID"         # input mode (default)
bsk upload @e20 --file ./a.png --mode drop --session "$SID"  # drop zone
bsk download @e7 --out ./export.csv --session "$SID"
```

### Health Checks and Fallback Retries

```bash
py -3 skill/scripts/doctor.py --wait-connected 20                 # no-side-effect environment check
py -3 skill/scripts/health_checker.py --session "$SID"            # session health report
py -3 skill/scripts/fallback_chain.py --session "$SID" --action observe
```

### User Tabs and Instance-Level Operations (fork build)

```bash
bsk browsers                                                    # take instance_id from here
bsk tab list --browser-id <instance_id> --scope user            # list user tabs
bsk tab observe --browser-id <instance_id> --tab-id 42 --expected-origin https://example.com
bsk browsers close --browser-id <instance_id> --confirm         # close a whole instance (use with care)
```

### Smart Wait

**Windows:**
```powershell
py -3 .\skill\scripts\wait_for.py --session demo `
  --url-contains "example.com" --timeout 10
py -3 .\skill\scripts\wait_for.py --session demo `
  --visible-text "saved" --timeout 10
```

**Linux / macOS:**
```bash
python3 ./skill/scripts/wait_for.py --session demo \
  --url-contains "example.com" --timeout 10
python3 ./skill/scripts/wait_for.py --session demo \
  --visible-text "completed" --timeout 10
```

### Daemon Smoke Test (No Side Effects)

**PowerShell:**
```powershell
bsk session start
$sessionId = bsk session start
bsk tab list --session $sessionId
bsk session stop $sessionId
```

**Bash:**
```bash
SESSION_ID=$(bsk session start)
bsk tab list --session $SESSION_ID
bsk session stop $SESSION_ID
```

---

## Privacy & Security

### Data Flow & Permission Boundary

```
Local AI agent
    │
    ▼
bsk CLI ──► 127.0.0.1:52800 daemon (WebSocket)
                │
                ▼
      Browser Extension + Real Tabs
```

**Helper Script Behavior Constraints:**

- ✅ Only send commands via `bsk` CLI
- ✅ Do not save cookies, passwords, auth tokens, or browser storage
- ✅ Do not contain telemetry or third-party analytics code
- ⚠️ Once snapshots/screenshots/PDFs are returned to the Agent, they enter the AI session processing scope

### Default Privacy Rules

1. **Minimal Read Principle** — Read only the minimum page content required to complete tasks
2. **Sensitive Data Protection** — Do not return cookies, Authorization headers, tokens, password fields, or browser storage
3. **Temporary File Cleanup** — Delete screenshots and PDFs after task completion (unless explicitly requested by user)
4. **Dangerous Operation Confirmation** — Must confirm before uploading, sending, publishing, purchasing, deleting, or changing permissions
5. **Do Not Bypass Security Mechanisms** — Do not bypass CAPTCHAs, paywalls, age restrictions, or browser warnings
6. **Human Intervention Mechanism** — Use `bsk request-help` for scenarios requiring human confirmation

### Multi-Browser Security Isolation

```bash
# List all connected browser instances
bsk browsers

# Start session on specific browser (independent isolation)
bsk session start --browser <instance-id-or-label>
bsk session start --browser-id <instance-id>   # exact routing, never resolves through a label
```

> If multiple browsers are connected but `--browser` is not specified, `bsk session start` will output available instance list.
>
> `bsk browsers close --browser-id <instance-id> --confirm` (fork build) closes **every** window of that instance — use it only when the user explicitly asks for it. Regular cleanup is `bsk session stop <id>`.
>
> **Warning:** This Skill can access real authentication states and should be treated as a high-privilege tool.

### External Dependencies Note

BrowserSkill daemon and browser extensions are external dependencies whose data processing behavior is not controlled by this repository.
Please review the privacy policy and implementation of the corresponding products before installation and use.

---

## Project Structure

```text
zenx-bridge-skill/
├── README.md                           # This document (English)
├── README_ZH.md                        # Chinese documentation
├── CHANGELOG.md                        # Version changelog
├── LICENSE                             # Open source license
├── AGENTS.md                           # Agent collaboration guidelines
├── docs/
│   └── v1.1.0-roadmap.md              # Version planning document
├── install.ps1                         # Windows one-click installer
├── install.sh                          # Linux/macOS one-click installer
├── Dockerfile                          # Docker multi-stage build
├── docker-compose.yml                 # Production environment orchestration
├── docker-compose.dev.yml             # Development environment orchestration
├── .dockerignore                       # Docker build ignore rules
│
├── skill/                              # 🔑 Core Skill Package
│   ├── SKILL.md                        # Agent execution instructions (must-read)
│   ├── agents/
│   │   └── openai.yaml                 # OpenAI/Codex metadata
│   ├── examples/                       # Workflow examples
│   │   ├── login_and_fill_form.md
│   │   ├── scroll_and_extract.md
│   │   ├── handle_popup.md
│   │   ├── network_debug.md
│   │   ├── record_and_replay.md
│   │   ├── long_screenshot.md
│   │   └── user_tab_and_scroll.md
│   ├── references/                     # Reference documents
│   │   ├── protocol.md                 # Command parameters and response formats
│   │   ├── operations.md               # Installation, status checks, fault recovery
│   │   ├── long-screenshot.md          # Full-page capture limits (0.2.4+)
│   │   ├── wheel.md                    # Native wheel input semantics (0.2.4+)
│   │   ├── scroll-to.md                # Element reveal + visible bounds (0.2.4+)
│   │   ├── operation-audit.md          # Local audit log scope and storage (0.2.4+)
│   │   ├── sandboxed-agents.md         # Shared daemon for sandboxed shells
│   │   ├── user-tab-control.md         # --browser-id user tabs (fork build)
│   │   └── how-it-works.md             # Architecture principles (for human maintainers)
│   └── scripts/
│       ├── invoke.ps1 / invoke.sh      # Invocation wrappers (auto-detect bsk invoke)
│       ├── doctor.py                   # Environment self-check (no side effects)
│       ├── snapshot.py                 # Page snapshot (compact / file / auto)
│       ├── screenshot.py / .ps1        # Screenshots (incl. --full-page)
│       ├── wait_for.py                 # Smart wait (URL / title / text)
│       ├── health_checker.py           # Session health diagnostics (v1.1.0 P0)
│       ├── fallback_chain.py           # Level-by-level fallback retries (v1.1.0 P0)
│       ├── record.ps1 / record.sh      # Record user actions
│       ├── replay.py                   # Replay a trace by semantic target
│       ├── network.ps1 / network.sh    # Network evidence (cursor-paginated)
│       ├── bsk_client.py               # bsk CLI abstraction layer
│       ├── error_codes.py              # Error classification (MVR)
│       ├── error_formatter.py          # Unified error/success envelopes
│       ├── retry_handler.py            # Exponential backoff retries
│       ├── timeout_manager.py          # Layered timeouts and cancellation
│       └── validator.py                # Input validation
│
└── tests/                              # Unit tests (292 passed / 1 skipped)
    ├── test_doctor.py
    ├── test_snapshot.py
    ├── test_screenshot.py
    ├── test_wait_for.py
    ├── test_health_checker.py
    ├── test_fallback_chain.py
    └── ...                             # MVR module tests
```

**Documentation Layering Guide:**

| Document | Target Audience | Load Timing |
|----------|---------------|-------------|
| `SKILL.md` | AI Agent | Loaded during every execution |
| `protocol.md` | Agent Developers | Loaded when querying parameters |
| `operations.md` | DevOps/Maintainers | Loaded during troubleshooting |
| `long-screenshot.md`, `wheel.md`, `scroll-to.md`, `operation-audit.md` | AI Agent | Loaded for that specific capability (0.2.4+) |
| `sandboxed-agents.md` | DevOps/Maintainers | Loaded when a sandbox reaps the daemon |
| `user-tab-control.md` | AI Agent | Loaded before touching a user's own tabs (fork build) |
| `how-it-works.md` | Human Maintainers | Not loaded for routine operations |

---

## Verification & Testing

### Unit Tests

```bash
python3 -m unittest discover -s tests -v
```

Current baseline: **292 passed / 1 skipped** (2026-09-17).

### PowerShell Syntax Check

```powershell
Get-ChildItem .\skill\scripts -Filter *.ps1 | ForEach-Object {
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName, [ref]$null, [ref]$errors
    ) | Out-Null
    if ($errors.Count) { throw $errors }
}
```

### Bash Syntax Check

```bash
bash -n skill/scripts/invoke.sh
```

### Codex Validator (Optional)

If you have Codex's `skill-creator` installed:

```powershell
py -3 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .\skill
```

### Doctor Self-Check (No Side Effects)

**Windows:**
```powershell
py -3 .\skill\scripts\doctor.py --wait-connected 20
```

**Linux / macOS:**
```bash
python3 ./skill/scripts/doctor.py --wait-connected 20
```

---

## Known Limitations

| Category | Description |
|----------|-------------|
| **Platform Compatibility** | PowerShell helpers primarily target Windows; other platforms can use bsk CLI directly |
| **Python Version** | Python helpers require Python 3.8+; Bash helpers require Bash 4.0+ |
| **Event Trust** | Synthetic clicks and inputs cannot satisfy websites requiring `event.isTrusted` |
| **Cross-Origin iframes** | Top-level page operations cannot directly access cross-origin iframe content |
| **Popup Blocking** | Browsers may block popups or new tabs that websites attempt to open |
| **Protocol Stability** | Response protocols may change after daemon and extension upgrades, requiring re-testing |
| **Windows Python** | On Windows, use `py -3` or `py` to start Python; do not assume `python3` command exists |
| **Capability Tiers** | `0.2.4+` and `fork build` capabilities are absent from a 0.2.3 release — confirm with `bsk <command> --help` first |
| **Protocol Gates** | `request-help` needs daemon protocol 1.3 and `tab borrow --timeout` needs 1.2; an older daemon fails fast with `unsupported_feature` |
| **Session Idle Timeout** | Sessions are reaped after 5 minutes idle — never a substitute for an explicit `bsk session stop` |
| **Rich-Text Editors** | `bsk fill` on `contenteditable` is plain-text replacement and may flatten existing markup |
| **Closing Instances** | `bsk browsers close` closes **every** window of that instance, is fork-build only, and is not a cleanup command |

---

## Roadmap

### Current Version: v1.1.0 (2026-09-17)

Delivered in two steps: the MVR reliability infrastructure (2026-07-17) — error classification (`error_codes.py`), structured JSON errors (`error_formatter.py`), input validation (`validator.py`), smart retry (`retry_handler.py`), timeout management (`timeout_manager.py`) — and the P0 completion (2026-09-08): session health monitoring (`health_checker.py`) and the graceful fallback chain (`fallback_chain.py`). **292 unit tests passing** (1 skipped).

Skill docs are aligned with **bsk CLI 0.2.3** (released 2026-09-08), daemon protocol 1.3. Commands merged after that tag — `screenshot --full-page`, `wheel`, `scroll-to`, `focus` / `blur`, `session start --name` — are labelled **0.2.4+** in the docs, and the `--browser-id` user-tab commands plus `bsk browsers close` are labelled **fork build only**; both need a build newer than 0.2.3 and are otherwise simply absent.

### Next: v1.2.0 (planned)

View the complete roadmap with planned features and priorities: [docs/v1.1.0-roadmap.md](docs/v1.1.0-roadmap.md)

**Remaining key areas:**

| Priority | Feature Area | Examples |
|----------|-------------|----------|
| **P1** | Performance Optimization | Concurrent session management, caching strategies, resource pooling |
| **P2** | Enhanced Actions | Drag-and-drop upload, file download, keyboard shortcut recording, multi-account profile switching |
| **P3** | Observability | Structured logging, Prometheus metrics, distributed tracing |

P0 (error recovery) shipped in v1.1.0.

---

## Contributing

We welcome community contributions! Please follow these guidelines when submitting modifications:

### Code Style Guidelines

1. **Python**: Follow existing patterns in `skill/scripts/`. Minimal comments, clear variable names
2. **PowerShell**: Use `[CmdletBinding()]`, named parameters, `-ErrorAction Stop`
3. **Bash**: `set -euo pipefail`. Quote all variables
4. **Markdown**: 2-space indentation, LF line endings

### Documentation Layering Principles

1. **Script comments** — Keep only minimal comments that help understand intent
2. **SKILL.md** — Only include steps Agents must execute and common issues
3. **Protocol details** — Go into `protocol.md`
4. **Lifecycle and recovery flows** — Go into `operations.md`

### Submission Workflow

1. Fork this repository
2. Create feature branch (`git checkout -b feat/amazing-feature`)
3. Commit changes (`but commit main -c -m "feat: add amazing feature"`)
4. Push to branch (`git push origin feat/amazing-feature`)
5. Create Pull Request

### Code of Conduct

- Respect privacy and security principles
- Test cross-platform compatibility of all Helper scripts
- Update relevant documentation (README, CHANGELOG, reference docs)
- Ensure CI/CD tests pass

---

## License

This project is open-sourced under the [MIT License](LICENSE).

**License Compliance:**
- This project is a derivative work of [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) (MIT License)
- All upstream license terms and attribution requirements are fully preserved
- The MIT License text is included in [LICENSE](LICENSE) file
- Third-party dependencies maintain their original licenses

## Disclaimer & Legal Notice

**Not an Official Tencent Product:**
- ZenX Bridge Skill is **NOT** developed, endorsed, or maintained by Tencent or any of its affiliates
- It is a community-driven project that builds upon the open-source BrowserSkill framework
- Use of this software is at your own risk

**Trademark & Branding:**
- "BrowserSkill" may be a trademark or registered trademark of Tencent
- "ZenX Bridge Skill" and related branding are used for identification purposes only
- No official association with or endorsement by Tencent is implied

**Security & Maintenance:**
- For **official security updates** and stable releases, please refer to [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill)
- Community-maintained versions may have different update cycles and support levels
- Always review code and security practices before using in production environments

## Project Lineage & Attribution

### Upstream Projects (Original Work)

| Project | Description | URL | License |
|---------|-------------|-----|---------|
| **BrowserSkill** | Original daemon + browser extension by Tencent | [github.com/Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | MIT |

### Direct Dependencies (Base Version)

| Project | Description | URL |
|---------|-------------|-----|
| **browserskill-new** | Enhanced base version with Windows fixes, multi-browser support, CI/CD workflows | [github.com/916938/zenx-bridge](https://github.com/916938/zenx-bridge) |

> **Note:** `browserskill-new` serves as the direct base for this Pro edition. It includes:
> - Windows platform compatibility improvements
> - Multi-browser instance management with smart labels
> - PR-based CI workflow integration
> - Enhanced error handling and logging
> - Fork-only capabilities: `bsk invoke` passthrough, Profile Templates, user-tab commands (`tab list|create|select --browser-id`, `tab observe`), and `bsk browsers close`

### This Edition (Pro Features)

**ZenX Bridge Skill** adds on top of `browserskill-new`:

- ✅ Complete multi-platform installation system (Windows PowerShell / Linux Bash / Docker)
- ✅ Support for 4+ AI Agent environments (CodeBuddy/Claude Code/WorkBuddy/Codex)
- ✅ Bilingual READMEs plus layered docs (`SKILL.md` → `protocol.md` → `operations.md` → 6 capability docs → `how-it-works.md`)
- ✅ Docker containerization with production orchestration
- ✅ **Health and degradation**: `health_checker.py` session health reports, `fallback_chain.py` level-by-level fallback
- ✅ **Record/replay and network evidence**: `record.sh` / `record.ps1` + `replay.py` (with `--dry-run`), `network.sh` / `network.ps1` with cursor pagination
- ✅ **Capability tiering**: every command labelled 0.2.3 / 0.2.4+ / fork build so agents never assume a feature is installed
- ✅ Privacy-focused design with explicit data handling rules
- ✅ Automated testing and verification tools (292 unit tests + PowerShell/Bash syntax checks + `doctor.py`)

### Supported Platforms

| Platform | Agent Environment | Installation Path |
|----------|------------------|-------------------|
| CodeBuddy | Primary | `~/.codebuddy/skills/zenx-bridge-skill` |
| Claude Code | Skills Mode | `~/.claude/skills/zenx-bridge-skill` |
| Claude Code | Commands Mode | `~/.claude/commands/zenx-bridge-skill` |
| WorkBuddy | Enterprise | `~/.workbuddy/skills/zenx-bridge-skill` |
| Codex | OpenAI | `~/.codex/skills/zenx-bridge-skill` |
| Docker | Containerized | `zenx-bridge-skill:latest` image |

## Acknowledgments

We extend our sincere gratitude to the following projects and communities:

### Core Technology
- **[Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill)** — The original daemon and browser extension that makes all of this possible. Thank you to the Tencent team for open-sourcing this incredible technology.
- **[916938/zenx-bridge](https://github.com/916938/zenx-bridge)** — The enhanced base version with critical Windows compatibility fixes and multi-browser support. The foundation upon which this Pro edition is built.

### AI Agent Platforms
- **[CodeBuddy](https://cnb.cool/codebuddy/codebuddy-code)** — Our primary supported AI Agent platform. Excellent integration experience.
- **[Claude Code](https://claude.ai/)** — Anthropic's AI coding assistant with dual-mode skill/command support.
- **WorkBuddy** — Enterprise-grade AI agent environment support.
- **Codex/OpenAI** — OpenAI's coding assistant with comprehensive metadata integration.

### Community & Contributors
- All **contributors** who have submitted issues, pull requests, and feedback
- **Users** who have tested and provided valuable improvement suggestions
- The **open-source community** for fostering innovation and collaboration

### Special Thanks
- To the **Tencent BrowserSkill team** for creating such a useful tool and making it open-source
- To the **AI Agent ecosystem developers** who make integrations like this possible
- To **you**, the user, for trusting this community-driven project

---

<div align="center">

**Made with ❤️ by the ZenX Bridge Skill Team**

[Report Issues](https://github.com/916938/zenx-bridge-skill/issues) · [Feature Requests](https://github.com/916938/zenx-bridge-skill/discussions) · [Changelog](CHANGELOG.md)

</div>
