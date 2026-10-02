<div align="center">

**[English](README.md) | 简体中文**

# ZenX Bridge Skill

**面向本地 AI Agent 的真实浏览器控制 Skill，强调隐私最小化和标签页安全**

[![Agent Skill](https://img.shields.io/badge/Agent-Skill-black.svg)](skill/SKILL.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#快速开始)
[![Version](https://img.shields.io/badge/Version-v1.1.0-green.svg)](CHANGELOG.md)
[![bsk](https://img.shields.io/badge/bsk-0.4.0%2B%20fork-orange.svg)](https://github.com/916938/zenx-bridge)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## 目录

- [简介](#简介)
- [特性](#特性)
- [版本兼容](#版本兼容)
- [快速开始](#快速开始)
- [安装指南](#安装指南)
  - [Windows 安装](#windows-安装-codebuddy--workbuddy--claude-code--codex)
  - [Linux/macOS 安装](#linuxmacos-安装-codebuddy--workbuddy--claude-code--codex)
  - [Docker 部署](#docker-容器化部署)
- [多环境支持](#多环境支持)
- [使用示例](#使用示例)
- [隐私与安全](#隐私与安全)
- [项目结构](#项目结构)
- [验证测试](#验证测试)
- [已知限制](#已知限制)
- [版本规划](#版本规划)
- [贡献指南](#贡献指南)

---

## 简介

ZenX Bridge Skill 是一个独立的 Agent Skill，通过本机 **BrowserSkill daemon** 控制用户**真实、已登录**的浏览器。

只要 Agent 能读取 Agent Skill 指令，并能执行本地 shell 命令，就可以使用核心工作流。本项目额外提供 OpenAI/Codex 元数据，但核心协议和操作说明不依赖某个特定 Agent 产品。

**当前对齐的 bsk 版本**：CLI 与浏览器扩展 **0.4.0**（daemon 协议 **1.3**）。自 0.2.2 起 CLI / 扩展 / DSH 插件共用同一 semver，升级时三者需同步，版本不一致会直接触发退出码 5。

> ⚠️ **本 skill 依赖 fork 构建** —— [`916938/zenx-bridge`](https://github.com/916938/zenx-bridge)，**不是**上游
> [`Tencent/BrowserSkill`](https://github.com/Tencent/BrowserSkill)。上游发布版**跑不起来**：本 skill 记录的若干命令只存在于
> fork（`browsers close`、`--browser-id` 系列 tab 管理、`tab observe`、`invoke`、`templates`、`completion`）。
> fork 使用独立版本线，号码始终高于最后一次同步的上游版本（上游 0.3.0 → fork 0.4.0），单看版本号即可分辨是哪个发行版。

### ⚠️ 项目来源与免责声明

> **重要声明：** 本项目是**社区驱动的衍生作品**，并非腾讯或其关联公司的官方产品。

**项目谱系：**

```
Tencent/BrowserSkill (官方版本)
        │
        ├──► 916938/zenx-bridge (社区分支与增强版)
        │           │
        │           └──► 916938/zenx-bridge-skill (本仓库 - Pro 专业版)
        │
        └──► 其他社区分支和衍生版本
```

**与上游项目的关系：**

| 仓库 | 角色 | 维护者 | 许可证 |
|------|------|--------|--------|
| [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | **原始/上游版本** | 腾讯（官方） | MIT |
| [916938/zenx-bridge](https://github.com/916938/zenx-bridge) | **增强基础版** | 社区（916938） | MIT |
| **916938/zenx-bridge-skill**（本仓库） | **Pro 专业版** | 社区（916938） | MIT |

**与官方版本的主要区别：**
- 本项目是 BrowserSkill 的**非官方、社区维护的增强版本**
- 增加了跨平台安装脚本（Windows/Linux/macOS）
- 提供了 Docker 部署解决方案
- 支持多种 AI Agent 环境（CodeBuddy/Claude Code/WorkBuddy/Codex）
- 包含完整的文档体系和分层架构
- 可能包含上游官方版本中没有的功能

**合规性说明：**
- ✅ 完全遵守 [MIT License](LICENSE) 条款
- ✅ 保持对上游项目的适当归属标注
- ❌ 未获得腾讯的背书、赞助或官方关联
- ⚠️ 用户应查看上游 [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) 获取官方发布和安全更新

如需获取包含 Windows 兼容性修复和多浏览器支持的最新稳定基础版本，请参见 [browserskill-new](https://github.com/916938/zenx-bridge)。

### 适用场景

- 阅读用户已经登录的网站
- 在现有标签页中搜索、点击和填写内容
- 保存页面截图或 PDF
- 排查点击后页面没有变化、后台标签页或弹窗拦截

### 架构概览

```
Local AI Agent (CodeBuddy / Claude Code / WorkBuddy / Codex)
       │
       ▼
   bsk CLI ──► 127.0.0.1:52800 daemon (WebSocket)
                    │
                    ▼
          浏览器扩展 + 真实 Chromium 标签页
```

> 本项目不是搜索引擎，也不包含浏览器驱动。它依赖 **BrowserSkill daemon** 和浏览器扩展，并在原有 skill 的基础上补充跨 Agent 工作流约束。

---

## 特性

| 特性 | 说明 |
|------|------|
| **会话生命周期** | `bsk session start` / `stop`，一个任务一个会话；5 分钟空闲超时仅作兜底，清理必须显式 `session stop` |
| **语义观察 observe** | `bsk observe` 返回 VOM 语义视图与新鲜 `@e` 引用，是默认首次观察；`--probe-hover` 探测 CSS 悬停菜单 |
| **标签页借用/归还** | `bsk tab borrow` / `bsk tab return` 安全借用用户标签页，用完立即归还 |
| **多浏览器与实例路由** | `bsk browsers` 列出实例，`--browser-id <instance_id>` 精确路由（smart label 只是可编辑别名，可能重复） |
| **丰富的交互命令** | `click` / `hover` / `fill` / `select` / `press` / `scroll-to` / `wheel` / `focus` / `blur` |
| **文件上传与下载** | `bsk upload`（input 与 `--mode drop` 两种机制）和 `bsk download`，文件经 daemon 中转，不碰浏览器内部路径 |
| **录制与重放** | `bsk record` 记录用户操作，`replay.py` 按语义目标重放（务必先 `--dry-run`） |
| **调试取证** | `network` / `console` 游标分页读取请求与日志；`screenshot`（含 `--full-page` 长截图）、`get-html` |
| **人工介入请求** | `bsk request-help` 请求用户处理 CAPTCHA、登录、OTP、支付确认 |
| **智能快照与等待** | `snapshot.py --auto` 自动选择精简/落盘，`wait_for.py` 按 URL、标题或可见文本轮询 |
| **健康诊断与降级** | `doctor.py` 无副作用自检；`health_checker.py` 会话级健康报告；`fallback_chain.py` 逐级降级重试 |
| **用户标签页只读观察** | `bsk tab observe --browser-id` 只读读取可见文本（fork 构建）：不注入脚本、不用 CDP、不碰表单与存储 |
| **关闭浏览器实例** | `bsk browsers close --browser-id <id> --confirm`（fork 构建）——只在用户明确要求时关闭整个实例 |
| **跨平台 helper** | Windows（PowerShell）与 Linux/macOS（Bash）helper，外加零第三方依赖的 Python helper |
| **隐私最小化** | 不读取 Cookie、Authorization、token、密码字段、浏览器存储与无关私人内容 |
| **分层文档** | `SKILL.md` → `protocol.md` → `operations.md` → 能力专档（长截图 / 滚轮 / scroll-to / 操作审计 / 沙箱 / 用户标签页） |

---

## 版本兼容

| 组件 | 最低 | 推荐 | 说明 |
|------|------|------|------|
| bsk CLI | 0.1.0 | **0.4.0**（fork 构建） | 低于 0.2.0 时 helper 自动回退到 legacy（直连子命令）模式 |
| 浏览器扩展 | 0.1.0 | **0.4.0**（fork 构建，须与 CLI 同版本） | CLI 与扩展版本不一致 → 退出码 5 |
| daemon 协议 | 1.2 | **1.3** | `request-help` 需要 1.3；`tab borrow --timeout` 需要 1.2 |
| Python | 3.8+ | 3.12+ | 仅 helper 脚本需要，零第三方依赖 |
| Node.js / pnpm | 18+ / 9.x | 20 LTS / 10.17.0 | 仅从源码构建扩展时需要 |

能力按**三个层级**发布，`SKILL.md` 与参考文档都会标注：

| 层级 | 含义 | 代表能力 |
|------|------|---------|
| **0.2.3** | 已发布基线（2026-09-08） | `observe`、`snapshot`、borrow/return、`request-help`、`record`、`network` / `console`、`upload` / `download`、`emulate`、`templates` |
| **0.2.4+** | 0.2.3 之后合入，需 2026-09-08 之后的构建 | `screenshot --full-page`、`wheel`、`scroll-to`、`focus` / `blur`、`session start --name` 与本地操作审计 |
| **fork 构建** | 仅 `916938/zenx-bridge`，上游发布版没有 | `tab list\|create\|select --browser-id`、`tab observe`、`browsers close`、`invoke`、`templates`、`completion`、`--since last_action`、profile account id、smart labels |

> fork 的 **0.4.0** 构建已同时包含 0.2.3 基线与 0.2.4+ 层级，装 fork 就一次拿到三层 —— 唯一例外是上游的 remote/server 模式：
> fork 虽携带该代码但**不支持**，在这里永远不算能力。若在更旧的构建上用到 0.2.4+ / fork 层级的能力，先跑 `bsk <命令> --help`
> 确认；缺失就用当前构建支持的方式继续。

---

## 快速开始

### 1. 安装 BrowserSkill（bsk CLI + daemon）

> 使用本 Skill 前需要安装本地 daemon 和浏览器扩展。当前对齐版本：**0.2.3**

**macOS / Linux：**
```bash
# 上游 Tencent/BrowserSkill
curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh

# 或 fork 版（推荐）：Pro 依赖的 bsk invoke、用户标签页命令等增强都在 fork 里
curl -fsSL https://raw.githubusercontent.com/916938/zenx-bridge/main/install.sh | sh
```

**Windows（PowerShell）：**
```powershell
irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex

# fork 版（推荐）
irm https://raw.githubusercontent.com/916938/zenx-bridge/main/install.ps1 | iex
```

**或通过 Cargo：**
```bash
cargo install bsk-cli
```

安装后确认版本：`bsk --version`（CLI 与扩展版本号必须一致，否则退出码 5）。

### 2. 安装浏览器扩展

从 [Chrome Web Store](https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi) 安装，或从源码构建：

```bash
cd <browser-skill-repo>
pnpm install && pnpm ext:build  # 输出: apps/extension/dist/chrome-mv3
```

然后在 Chrome 中加载已解压的扩展程序（`chrome://extensions` → 开发者模式 → 加载已解压的扩展程序）。

> 详细构建步骤请参阅 [operations.md - Building the extension from source](skill/references/operations.md#building-the-extension-from-source)

用 `bsk doctor` 确认 daemon、端口与扩展连接都正常。

### 3. 安装本 Skill

**自动安装（推荐）：** `bsk install-skill` 会把 skill 写进本机已识别的 Agent 环境：

```bash
bsk install-skill --list        # 查看可安装的 Agent harness
bsk install-skill --all         # 全部安装
bsk install-skill --source <path>   # 安装自定义 SKILL.md（会暂停 skill 自动更新）
```

**手动安装：** 将仓库中的 `skill/` 目录复制到你的 Agent skills 目录：

```text
<agent-skills-directory>/
└── zenx-bridge-skill/
    ├── SKILL.md          # 核心 Agent 指令
    ├── scripts/          # Python/Bash/PowerShell helpers
    ├── examples/         # 工作流样例
    └── references/       # 协议和操作文档
```

### 4. 自检验证

**Windows：**
```powershell
py -3 <your-path>\zenx-bridge-skill\scripts\doctor.py --wait-connected 20
```

**Linux / macOS：**
```bash
python3 <your-path>/zenx-bridge-skill/scripts/doctor.py --wait-connected 20
```

预期输出：
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

### 5. 开始使用

在 Agent 对话框中输入：

```text
使用 $zenx-bridge-skill 查看我当前登录的网页
```

```text
使用 $zenx-bridge-skill 在知乎页面搜索 OpenAI
```

```text
使用 $zenx-bridge-skill 截取当前页面，并在完成后删除临时文件
```

---

## 安装指南

### Windows 安装（CodeBuddy / WorkBuddy / Claude Code / Codex）

#### 方法一：Git 克隆 + 手动复制（推荐）

```powershell
# 1. 克隆仓库
git clone https://github.com/916938/zenx-bridge-skill.git %TEMP%\bsk-install

# 2. 复制到目标路径（根据你的 Agent 环境选择）
$target = "$env:USERPROFILE\.codebuddy\skills\zenx-bridge-skill"     # CodeBuddy
# $target = "$env:USERPROFILE\.workbuddy\skills\zenx-bridge-skill"   # WorkBuddy
# $target = "$env:USERPROFILE\.claude\skills\zenx-bridge-skill"      # Claude Code (Skills)
# $target = "$env:USERPROFILE\.claude\commands\zenx-bridge-skill"    # Claude Code (Commands)
# $target = "$env:USERPROFILE\.codex\skills\zenx-bridge-skill"        # Codex

New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item "%TEMP%\bsk-install\skill\*" -Destination $target -Recurse -Force

# 3. 清理并验证
Remove-Item -Recurse -Force %TEMP%\bsk-install
Test-Path "$target\SKILL.md"
```

#### 方法二：PowerShell 一键脚本（自动化）

```powershell
# 直接下载并执行
irm https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.ps1 | iex

# 或保存后运行（可审查代码）
irm https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.ps1 -OutFile install.ps1
.\install.ps1 -Branch main

# 强制覆盖已有安装
.\install.ps1 -Branch main -Force
```

脚本功能：
- ✅ 自动检测 Agent 环境（CodeBuddy / WorkBuddy / Claude Code / Codex）
- ✅ 支持强制覆盖（带备份）
- ✅ 安装后自动验证
- ✅ 彩色输出和错误提示

#### 方法三：手动下载 ZIP

1. 访问 https://github.com/916938/zenx-bridge-skill
2. 点击 **Code** → **Download ZIP**
3. 解压后复制 `skill/` 目录内容到目标路径

---

### Linux/macOS 安装（CodeBuddy / WorkBuddy / Claude Code / Codex）

#### 前置条件

```bash
# 检查必要工具
git --version && python3 --version && curl --version

# 如缺少依赖，按系统安装：
# Ubuntu/Debian: sudo apt update && sudo apt install -y git python3 curl
# macOS: brew install git python3 curl
# Fedora: sudo dnf install -y git python3 curl
# Arch: sudo pacman -S git python3 curl
```

#### 方法一：Git 克隆 + 手动复制（推荐）

```bash
# 1. 克隆仓库
TMPDIR=$(mktemp -d)
git clone https://github.com/916938/zenx-bridge-skill.git "$TMPDIR/bsk"

# 2. 选择目标路径（根据你的 Agent 环境）
TARGET="$HOME/.codebuddy/skills/zenx-bridge-skill"           # CodeBuddy
# TARGET="$HOME/.workbuddy/skills/zenx-bridge-skill"         # WorkBuddy
# TARGET="$HOME/.claude/skills/zenx-bridge-skill"            # Claude Code (Skills)
# TARGET="$HOME/.claude/commands/zenx-bridge-skill"          # Claude Code (Commands)
# TARGET="$HOME/.codex/skills/zenx-bridge-skill"             # Codex

# 3. 复制文件
mkdir -p "$(dirname "$TARGET")"
cp -r "$TMPDIR/bsk/skill/." "$TARGET"

# 4. 清理并验证
rm -rf "$TMPDIR"
test -f "$TARGET/SKILL.md" && echo "✅ 安装成功！"
```

#### 方法二：Bash 一键脚本（自动化）

```bash
# 方式 A：直接执行
curl -fsSL https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.sh | bash

# 方式 B：下载后执行（推荐）
curl -fsSL https://raw.githubusercontent.com/916938/zenx-bridge-skill/main/install.sh -o install.sh
chmod +x install.sh
./install.sh --branch main

# 高级选项
./install.sh --force                          # 强制覆盖
./install.sh --dry-run                        # 试运行（不实际安装）
./install.sh --target-path "/custom/path"     # 自定义路径
./install.sh -v                               # 详细输出
```

#### 方法三：手动下载 ZIP

```bash
# 1. 下载并解压
cd ~/Downloads
unzip zenx-bridge-skill-main.zip -d /tmp/bsk-install

# 2. 复制文件
ZIP_EXTRACT="/tmp/bsk-install/zenx-bridge-skill-main"
TARGET="$HOME/.codebuddy/skills/zenx-bridge-skill"
mkdir -p "$(dirname "$TARGET")"
cp -r "$ZIP_EXTRACT/skill/." "$TARGET"

# 3. 验证
test -f "$TARGET/SKILL.md" && echo "✅ 安装成功！"
```

---

### Docker 容器化部署

适用于 CI/CD、隔离环境、统一部署场景。

#### 前置条件

```bash
docker --version        # Docker Engine 20.10+
docker compose version  # Docker Compose V2+
```

#### 方式一：单容器快速启动（推荐入门）

```bash
# 1. 构建镜像
git clone https://github.com/916938/zenx-bridge-skill.git
cd zenx-bridge-skill
docker build -t zenx-bridge-skill:latest .

# 2. 运行自检（需连接宿主机上的 bsk daemon）
docker run --rm \
  --network host \
  -v ~/.bsk:/app/.bsk:ro \
  zenx-bridge-skill:latest python3 skill/scripts/doctor.py --wait-connected 20

# 3. 执行 snapshot 示例
docker run --rm --network host \
  zenx-bridge-skill:latest python3 skill/scripts/snapshot.py --session demo --auto
```

**常用参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `--network host` | 使用宿主机网络访问本地 daemon | 必需 |
| `-v` | 挂载卷（数据持久化） | `-v ./data:/app/data` |
| `-e` | 设置环境变量 | `-e LOG_LEVEL=DEBUG` |
| `--rm` | 退出后自动删除容器 | 测试时推荐 |
| `-d` | 后台运行 | 生产环境推荐 |

#### 方式二：Docker Compose 编排（生产环境）

包含 **daemon + Chrome + Redis + 监控** 的完整部署：

```bash
# 启动所有服务
docker compose up -d

# 仅启动核心服务（不含监控）
docker compose up -d bsk-daemon zenx-bridge-skill redis chrome-browser

# 启动开发环境（源代码热挂载）
docker compose -f docker-compose.dev.yml up --build -d

# 启动带监控的完整环境
docker compose --profile monitoring up -d

# 访问 Grafana 仪表板
# http://localhost:3000 (默认: admin/admin)
```

**架构图：**

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
│  │   redis  │          │ monitoring  │ (Grafana, 可选)      │
│  │ :6379    │          │ :3000       │                      │
│  └──────────┘          └─────────────┘                      │
│                                                             │
│  Volumes: data, screenshots, snapshots, chrome-profile, grafana│
└─────────────────────────────────────────────────────────────┘
```

**自定义配置（`.env` 文件）：**

```bash
BSK_AUTH_TOKEN=your-secure-token-here
BSK_MAX_SESSIONS=20
CHROME_MODE=headed              # 或 headless
LOG_LEVEL=INFO                  # DEBUG, INFO, WARN, ERROR
DOCKER_CPUS_LIMIT=2.0
DOCKER_MEMORY_LIMIT=4G
```

#### 方式三：CI/CD 集成

**GitHub Actions 示例（`.github/workflows/docker-test.yml`）：**

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

#### 性能优化与安全加固

**减小镜像体积：** 多阶段构建已实现在 Dockerfile 中

**利用缓存层：** 已优化 `.dockerignore`

**生产安全加固（补充配置）：**

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

**故障排除：**

| 问题 | 可能原因 | 解决方案 |
|------|---------|----------|
| 无法连接 daemon | 网络模式错误 | 使用 `--network host` |
| 权限被拒绝 | 卷挂载权限问题 | 调整 UID (`user: "1000:1000"`) |
| Chrome 无法启动 | 缺少共享内存 | 增加 `shm_size: '2gb'` |
| 容器重启循环 | 健康检查失败 | 查看日志 `docker compose logs <service>` |

**镜像管理：**

```bash
# 多平台构建
docker buildx build --platform linux/amd64,linux/arm64 -t zenx-bridge-skill:latest .

# 推送到仓库
docker tag zenx-bridge-skill:latest ghcr.io/916938/zenx-bridge-skill:v1.0.0
docker push ghcr.io/916938/zenx-bridge-skill:v1.0.0

# 导出/导入（离线环境）
docker save -o zenx-bridge-skill.tar zenx-bridge-skill:latest
docker load -i zenx-bridge-skill.tar
```

---

## 多环境支持

本 Skill 支持 **CodeBuddy、WorkBuddy、Claude Code、Codex** 四大 AI Agent 平台：

| Agent 平台 | Skills 路径 | Commands 路径 | 备注 |
|-----------|------------|---------------|------|
| **CodeBuddy** | `~/.codebuddy/skills/zenx-bridge-skill` | - | 主要支持平台 |
| **Claude Code** | `~/.claude/skills/zenx-bridge-skill` | `~/.claude/commands/zenx-bridge-skill` | 双模式支持（推荐 Skills） |
| **WorkBuddy** | `~/.workbuddy/skills/zenx-bridge-skill` | - | 企业级 Agent |
| **Codex** | `~/.codex/skills/zenx-bridge-skill` | - | OpenAI 编程助手 |

### 自动检测优先级

当使用一键安装脚本时，自动检测顺序为：
**CodeBuddy > Claude Code > WorkBuddy > Codex**

可通过环境变量或命令行参数覆盖默认路径：

```bash
# Linux/macOS
CODEBUDDY_SKILLS_DIR=/custom/path ./install.sh
./install.sh --target-path "$HOME/.my-agent/skills/zenx-bridge-skill"

# Windows
$env:CODEBUDDY_SKILLS_DIR="C:\Custom\Path"
.\install.ps1
```

### 卸载

```bash
# Linux/macOS
rm -rf ~/.codebuddy/skills/zenx-bridge-skill

# PowerShell
Remove-Item -Recurse -Force "$env:USERPROFILE\.codebuddy\skills\zenx-bridge-skill"
```

---

## 使用示例

### 页面快照

**Windows：**
```powershell
# 精简模式（适合定位元素）
py -3 .\skill\scripts\snapshot.py --session demo --auto
py -3 .\skill\scripts\snapshot.py --session demo --mode compact

# 完整模式（写入临时文件）
py -3 .\skill\scripts\snapshot.py --session demo --mode file
```

**Linux / macOS：**
```bash
python3 ./skill/scripts/snapshot.py --session demo --auto
python3 ./skill/scripts/snapshot.py --session demo --mode file
```

### 截图

**Windows：**
```powershell
py -3 .\skill\scripts\screenshot.py --session demo
# 全页长截图（0.2.4+，默认 2 分钟截止时间）
py -3 .\skill\scripts\screenshot.py --session demo --full-page --out page.png
```

**Linux / macOS：**
```bash
python3 ./skill/scripts/screenshot.py --session demo
python3 ./skill/scripts/screenshot.py --session demo --full-page --out page.png
```

> `--full-page` 与 `--selector` 互斥；细节见 [references/long-screenshot.md](skill/references/long-screenshot.md)。

### 语义观察（推荐首选）

```bash
bsk observe --session demo                 # VOM 语义视图 + @e 引用
bsk observe --session demo --probe-hover   # 预期控件缺失且无悬停标记时用一次（0.2.2+）
bsk scroll-to @e3 --session demo           # 滚动元素入视口（0.2.4+）
bsk wheel --delta-y 600 --session demo     # 原生滚轮事件（0.2.4+）
```

### 录制与重放

```bash
scripts/record.sh start --purpose "publish an article" --output ./flow.json
SID=$(bsk session start)
python3 scripts/replay.py ./flow.json --session "$SID" --dry-run   # 先检查计划
python3 scripts/replay.py ./flow.json --session "$SID"              # 再执行
bsk session stop "$SID"
```

### 网络与控制台取证

```bash
scripts/network.sh --session "$SID" --limit 20 --json   # 下一次用 --since <游标> 增量拉取
bsk console --session "$SID"
```

### 文件上传与下载（0.2.2+）

```bash
bsk upload @e12 --file ./report.pdf --session "$SID"        # input 模式（默认）
bsk upload @e20 --file ./a.png --mode drop --session "$SID" # 拖放区
bsk download @e7 --out ./export.csv --session "$SID"
```

### 健康诊断与降级重试

```bash
py -3 skill/scripts/doctor.py --wait-connected 20               # 无副作用环境自检
py -3 skill/scripts/health_checker.py --session "$SID"          # 会话健康报告
py -3 skill/scripts/fallback_chain.py --session "$SID" --action observe
```

### 用户标签页与实例级操作（fork 构建）

```bash
bsk browsers                                                    # 取 instance_id
bsk tab list --browser-id <instance_id> --scope user            # 列出用户标签页
bsk tab observe --browser-id <instance_id> --tab-id 42 --expected-origin https://example.com
bsk browsers close --browser-id <instance_id> --confirm         # 关闭整个实例（慎用）
```

### 智能等待

**Windows：**
```powershell
py -3 .\skill\scripts\wait_for.py --session demo `
  --url-contains "example.com" --timeout 10
py -3 .\skill\scripts\wait_for.py --session demo `
  --visible-text "已保存" --timeout 10
```

**Linux / macOS：**
```bash
python3 ./skill/scripts/wait_for.py --session demo \
  --url-contains "example.com" --timeout 10
python3 ./skill/scripts/wait_for.py --session demo \
  --visible-text "已完成" --timeout 10
```

### Daemon 冒烟测试（无副作用）

**PowerShell：**
```powershell
bsk session start
$sessionId = bsk session start
bsk tab list --session $sessionId
bsk session stop $sessionId
```

**Bash：**
```bash
SESSION_ID=$(bsk session start)
bsk tab list --session $SESSION_ID
bsk session stop $SESSION_ID
```

---

## 隐私与安全

### 数据流与权限边界

```
Local AI agent
    │
    ▼
bsk CLI ──► 127.0.0.1:52800 daemon (WebSocket)
                │
                ▼
      浏览器扩展和真实标签页
```

**Helper 脚本行为约束：**

- ✅ 只通过 `bsk` CLI 发送命令
- ✅ 不保存 Cookie、密码、认证令牌或浏览器存储
- ✅ 不包含遥测或第三方分析代码
- ⚠️ 截图/快照/PDF 返回给 Agent 后进入 AI 会话处理范围

### 默认隐私规则

1. **最少读取原则** — 只读取完成任务所需的最少页面内容
2. **敏感信息保护** — 不返回 Cookie、Authorization、token、密码字段或浏览器存储
3. **临时文件清理** — 截图和 PDF 任务完成后删除（除非用户明确要求保留）
4. **危险操作确认** — 上传、发送、发布、购买、删除和权限变更前必须确认
5. **不绕过安全机制** — 不绕过验证码、付费墙、年龄限制、浏览器警告
6. **人工介入机制** — 使用 `bsk request-help` 处理需要人工确认的场景

### 多浏览器安全隔离

```bash
# 列出所有已连接的浏览器实例
bsk browsers

# 在指定浏览器上启动会话（独立隔离）
bsk session start --browser <instance-id-or-label>
bsk session start --browser-id <instance-id>   # 精确路由，绝不经过 label 解析
```

> 如果连接多个浏览器但未指定 `--browser`，`bsk session start` 会输出可用实例列表。
>
> `bsk browsers close --browser-id <instance-id> --confirm`（fork 构建）会关闭该实例的**所有**窗口，
> 只能在用户明确要求时使用；常规收尾请用 `bsk session stop <id>`。
>
> **警告：** 此 Skill 能访问真实登录态，应按高权限工具对待。

### 外部依赖说明

BrowserSkill daemon 和浏览器扩展是外部依赖，其数据处理行为不受本仓库控制。
安装和使用前请审阅对应产品的隐私政策与实现。

---

## 项目结构

```text
zenx-bridge-skill/
├── README.md                           # 本文档
├── CHANGELOG.md                        # 版本更新日志
├── LICENSE                             # 开源许可证
├── AGENTS.md                           # Agent 协作规范
├── docs/
│   └── v1.1.0-roadmap.md              # 版本规划文档
├── install.ps1                         # Windows 一键安装脚本
├── install.sh                          # Linux/macOS 一键安装脚本
├── Dockerfile                          # Docker 多阶段构建
├── docker-compose.yml                 # 生产环境编排
├── docker-compose.dev.yml             # 开发环境编排
├── .dockerignore                       # Docker 构建忽略规则
│
├── skill/                              # 🔑 核心技能包
│   ├── SKILL.md                        # Agent 执行指令（必读）
│   ├── agents/
│   │   └── openai.yaml                 # OpenAI/Codex 元数据
│   ├── examples/                       # 工作流样例
│   │   ├── login_and_fill_form.md
│   │   ├── scroll_and_extract.md
│   │   ├── handle_popup.md
│   │   ├── network_debug.md
│   │   ├── record_and_replay.md
│   │   ├── long_screenshot.md
│   │   └── user_tab_and_scroll.md
│   ├── references/                     # 参考文档
│   │   ├── protocol.md                 # 命令参数与响应格式
│   │   ├── operations.md               # 安装、状态检查、故障恢复
│   │   ├── long-screenshot.md          # 全页长截图限制与契约（0.2.4+）
│   │   ├── wheel.md                    # 原生滚轮事件语义（0.2.4+）
│   │   ├── scroll-to.md                # 元素滚动入视口与可见矩形（0.2.4+）
│   │   ├── operation-audit.md          # 本地操作审计的记录范围与存储（0.2.4+）
│   │   ├── sandboxed-agents.md         # 沙箱环境下共享 daemon
│   │   ├── user-tab-control.md         # --browser-id 操作用户标签页（fork 构建）
│   │   └── how-it-works.md             # 架构原理（人类维护者阅读）
│   └── scripts/
│       ├── invoke.ps1 / invoke.sh      # 调用封装（自动识别 bsk invoke）
│       ├── doctor.py                   # 环境自检（无副作用）
│       ├── snapshot.py                 # 页面快照（compact / file / auto）
│       ├── screenshot.py / .ps1        # 截图（含 --full-page 长截图）
│       ├── wait_for.py                 # 智能等待（URL / 标题 / 文本）
│       ├── health_checker.py           # 会话健康诊断（v1.1.0 P0）
│       ├── fallback_chain.py           # 逐级降级重试（v1.1.0 P0）
│       ├── record.ps1 / record.sh      # 录制用户操作
│       ├── replay.py                   # 按语义目标重放 trace
│       ├── network.ps1 / network.sh    # 网络请求取证（游标分页）
│       ├── bsk_client.py               # bsk CLI 封装层
│       ├── error_codes.py              # 错误分类（MVR）
│       ├── error_formatter.py          # 统一错误/成功信封
│       ├── retry_handler.py            # 指数退避重试
│       ├── timeout_manager.py          # 分层超时与取消
│       └── validator.py                # 输入校验
│
└── tests/                              # 单元测试（292 passed / 1 skipped）
    ├── test_doctor.py
    ├── test_snapshot.py
    ├── test_screenshot.py
    ├── test_wait_for.py
    ├── test_health_checker.py
    ├── test_fallback_chain.py
    └── ...                             # MVR 模块测试
```

**文档分层说明：**

| 文档 | 目标读者 | 加载时机 |
|------|---------|---------|
| `SKILL.md` | AI Agent | 每次执行时加载 |
| `protocol.md` | Agent 开发者 | 参数查询时加载 |
| `operations.md` | DevOps/维护者 | 故障排查时加载 |
| `long-screenshot.md`、`wheel.md`、`scroll-to.md`、`operation-audit.md` | AI Agent | 用到该能力时加载（0.2.4+） |
| `sandboxed-agents.md` | DevOps/维护者 | 沙箱会回收 daemon 时加载 |
| `user-tab-control.md` | AI Agent | 需要操作用户自有标签页时加载（fork 构建） |
| `how-it-works.md` | 人类维护者 | 仅架构理解时不加载 |

---

## 验证测试

### 单元测试

```bash
python3 -m unittest discover -s tests -v
```

当前基线：**292 passed / 1 skipped**（2026-09-17）。

### PowerShell 语法检查

```powershell
Get-ChildItem .\skill\scripts -Filter *.ps1 | ForEach-Object {
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName, [ref]$null, [ref]$errors
    ) | Out-Null
    if ($errors.Count) { throw $errors }
}
```

### Bash 语法检查

```bash
bash -n skill/scripts/invoke.sh
```

### Codex 校验器（可选）

若安装了 Codex 的 `skill-creator`：

```powershell
py -3 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .\skill
```

### Doctor 自检（无副作用）

**Windows：**
```powershell
py -3 .\skill\scripts\doctor.py --wait-connected 20
```

**Linux / macOS：**
```bash
python3 ./skill/scripts/doctor.py --wait-connected 20
```

---

## 已知限制

| 限制类别 | 详细说明 |
|---------|---------|
| **平台兼容性** | PowerShell helper 以 Windows 为主；其他平台可通过 bsk CLI 调用 |
| **Python 版本** | Python helper 需要 Python 3.8+；Bash helper 需要 Bash 4.0+ |
| **事件信任** | 合成点击和输入无法满足要求 `event.isTrusted` 的网站 |
| **跨域 iframe** | 顶层页面操作不能直接访问跨域 iframe 内容 |
| **弹窗拦截** | 浏览器可能拦截站点尝试打开的弹窗或新标签页 |
| **协议稳定性** | daemon 和扩展升级后，响应协议可能发生变化，需要重新实测 |
| **Windows Python** | Windows 应使用 `py -3` 或 `py` 启动 Python，不要假定存在 `python3` 命令 |
| **能力分层** | `0.2.4+` 与 `fork 构建` 的能力不在 0.2.3 发布版里，用前需 `bsk <命令> --help` 确认 |
| **协议门槛** | `request-help` 需要 daemon 协议 1.3，`tab borrow --timeout` 需要 1.2；旧 daemon 直接报 `unsupported_feature` |
| **会话空闲超时** | 会话空闲 5 分钟后会被回收，不能代替显式 `bsk session stop` |
| **富文本编辑** | `bsk fill` 在 `contenteditable` 上是纯文本替换，会丢失/压平富文本格式 |
| **关闭实例** | `bsk browsers close` 会关闭该实例的**所有**窗口（含未触碰过的），仅 fork 构建可用，不能当清理手段 |

---

## 版本规划

### 当前版本：v1.1.0（2026-09-17）

对齐 bsk CLI / 扩展 **0.2.3**（daemon 协议 1.3）与 0.2.3 之后合入的能力，并完成 v1.1.0 的 P0 可靠性工作
（`health_checker.py`、`fallback_chain.py`）。详见 [CHANGELOG.md](CHANGELOG.md)。

### 下个版本：v1.2.0（规划中）

查看完整的 23 项功能规划和优先级：[docs/v1.1.0-roadmap.md](docs/v1.1.0-roadmap.md)

**剩余方向：**

| 优先级 | 功能领域 | 示例 |
|-------|---------|------|
| **P1** | 性能优化 | 并发会话管理、缓存策略、资源池化 |
| **P2** | 增强动作 | 拖拽上传、文件下载、键盘快捷键录制；多账户 Profile 切换 |
| **P3** | 可观测性 | 结构化日志、Prometheus 指标、分布式追踪 |

P0（错误恢复：重试机制、断点续传、优雅降级）已在 v1.1.0 交付。

---

## 贡献指南

我们欢迎社区贡献！提交修改前请遵循以下规范：

### 代码风格

1. **Python**: 遵循现有 `skill/scripts/` 中的模式。最小注释，清晰变量名
2. **PowerShell**: 使用 `[CmdletBinding()]`, 命名参数, `-ErrorAction Stop`
3. **Bash**: `set -euo pipefail`. 所有变量加引号
4. **Markdown**: 2-space 缩进, LF 行结尾

### 文档分层原则

1. **脚本注释** — 只保留帮助理解意图的最小注释
2. **SKILL.md** — 只写 Agent 必须执行的步骤和常见问题
3. **协议细节** — 进入 `protocol.md`
4. **生命周期与恢复流程** — 进入 `operations.md`

### 提交流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交更改 (`but commit main -c -m "feat: add amazing feature"`)
4. 推送到分支 (`git push origin feat/amazing-feature`)
5. 创建 Pull Request

### 行为准则

- 尊重隐私和安全原则
- 测试所有 Helper 脚本的跨平台兼容性
- 更新相关文档（README、CHANGELOG、参考文档）
- 确保 CI/CD 测试通过

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

**许可证合规性：**
- 本项目是 [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) 的衍生作品（MIT 许可证）
- 完全保留上游许可证的所有条款和归属要求
- MIT 许可证全文包含在 [LICENSE](LICENSE) 文件中
- 第三方依赖库保持其原始许可证

## 免责声明与法律提示

**非腾讯官方产品：**
- ZenX Bridge Skill **并非**由腾讯或其关联公司开发、背书或维护
- 这是一个基于开源 BrowserSkill 框架构建的社区驱动项目
- 使用本软件的风险由用户自行承担

**商标与品牌：**
- "BrowserSkill" 可能是腾讯的商标或注册商标
- "ZenX Bridge Skill" 及相关品牌仅用于识别目的
- 不暗示与腾讯有任何官方关联或背书

**安全性与维护：**
- 如需**官方安全更新**和稳定版本，请参阅 [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill)
- 社区维护版本可能具有不同的更新周期和支持级别
- 在生产环境中使用前请务必审查代码和安全实践

## 项目谱系与归属

### 上游项目（原创工作）

| 项目 | 描述 | URL | 许可证 |
|------|------|-----|--------|
| **BrowserSkill** | 腾讯官方 daemon + 浏览器扩展 | [github.com/Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | MIT |

### 直接依赖（基础版本）

| 项目 | 描述 | URL |
|------|------|-----|
| **browserskill-new** | 包含 Windows 修复、多浏览器支持、CI/CD 工作流的增强基础版 | [github.com/916938/zenx-bridge](https://github.com/916938/zenx-bridge) |

> **说明：** `browserskill-new` 是本 Pro 版的直接基础。它包括：
> - Windows 平台兼容性改进
> - 多浏览器实例管理与 smart label
> - 基于 PR 的 CI 工作流集成
> - 增强的错误处理和日志记录
> - fork 专属能力：`bsk invoke` 透传、Profile Templates、用户标签页命令（`tab list|create|select --browser-id`、`tab observe`）、`bsk browsers close`

### 本版本（Pro 功能）

**ZenX Bridge Skill** 在 `browserskill-new` 基础上新增：

- ✅ 完整的跨平台安装系统（Windows PowerShell / Linux Bash / Docker）
- ✅ 支持 4+ 种 AI Agent 环境（CodeBuddy/Claude Code/WorkBuddy/Codex）
- ✅ 双语 README + 分层文档体系（`SKILL.md` → `protocol.md` → `operations.md` → 6 份能力专档 → `how-it-works.md`）
- ✅ Docker 容器化及生产环境编排
- ✅ **健康诊断与优雅降级**：`health_checker.py` 会话健康报告、`fallback_chain.py` 逐级降级重试
- ✅ **录制重放与网络取证**：`record.sh` / `record.ps1` + `replay.py`（先 `--dry-run`）、`network.sh` / `network.ps1` 游标分页
- ✅ **能力分层标注**：每个命令标注 0.2.3 / 0.2.4+ / fork 构建，避免 Agent 假设装了就有
- ✅ 以隐私为核心的设计和明确的数据处理规则
- ✅ 自动化测试与验证工具（292 单测 + PowerShell/Bash 语法检查 + `doctor.py` 自检）

### 支持的平台

| 平台 | Agent 环境 | 安装路径 |
|------|-----------|---------|
| CodeBuddy | 主要支持平台 | `~/.codebuddy/skills/zenx-bridge-skill` |
| Claude Code | Skills 模式 | `~/.claude/skills/zenx-bridge-skill` |
| Claude Code | Commands 模式 | `~/.claude/commands/zenx-bridge-skill` |
| WorkBuddy | 企业级 Agent | `~/.workbuddy/skills/zenx-bridge-skill` |
| Codex | OpenAI 助手 | `~/.codex/skills/zenx-bridge-skill` |
| Docker | 容器化部署 | `zenx-bridge-skill:latest` 镜像 |

## 致谢

我们向以下项目和社区致以诚挚的感谢：

### 核心技术
- **[Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill)** — 使这一切成为可能的原始 daemon 和浏览器扩展。感谢腾讯团队开源了这项令人难以置信的技术。
- **[916938/zenx-bridge](https://github.com/916938/zenx-bridge)** — 包含关键 Windows 兼容性修复和多浏览器支持的增强基础版。本 Pro 版本构建的基础。

### AI Agent 平台
- **[CodeBuddy](https://cnb.cool/codebuddy/codebuddy-code)** — 我们主要支持的 AI Agent 平台。出色的集成体验。
- **[Claude Code](https://claude.ai/)** — Anthropic 的 AI 编程助手，支持双模式 skill/command。
- **WorkBuddy** — 企业级 AI agent 环境支持。
- **Codex/OpenAI** — OpenAI 的编程助手，提供全面的元数据集成。

### 社区与贡献者
- 所有提交 issue、pull request 和反馈的**贡献者**
- 进行测试并提供宝贵改进建议的**用户**
- 促进创新和协作的**开源社区**

### 特别感谢
- 感谢 **Tencent BrowserSkill 团队**创建了如此有用的工具并将其开源
- 感谢使此类集成成为可能的 **AI Agent 生态系统开发者**
- 感谢**您**，用户，信任这个社区驱动的项目

---

<div align="center">

**Made with ❤️ by the ZenX Bridge Skill Team**

[报告问题](https://github.com/916938/zenx-bridge-skill/issues) · [提出建议](https://github.com/916938/zenx-bridge-skill/discussions) · [更新日志](CHANGELOG.md)

</div>
