# Changelog

### 声明依赖 fork 构建，并跟进 fork 0.4.0 版本线（2026-09-19）

`browserskill-new` 已明确定位为 **soft fork（下游发行版）**，版本线独立：号码始终高于最后一次同步的上游版本（上游 0.3.0 → fork **0.4.0**）。Pro 侧同步：

- **两份 README + `skill/SKILL.md` 新增显式声明**：本 skill 依赖 `916938/zenx-bridge` 的 fork 构建，**上游 `Tencent/BrowserSkill` 发布版跑不起来** —— 本 skill 记录的 `browsers close`、`--browser-id` 系列 tab 管理、`tab observe`、`invoke`、`templates`、`completion` 只存在于 fork。
- 版本推荐值 0.2.3 → **0.4.0**（badge、版本兼容表、SKILL.md 版本块）。
- **fork 层级能力清单补全**：在原来 3 条基础上补 `invoke`、`templates`、`completion`、`--since last_action`、profile account id、smart labels。
- 新增说明：fork 的 0.4.0 已同时包含 0.2.3 基线与 0.2.4+ 层级；**唯一例外是上游 remote/server 模式 —— fork 携带但不支持，不算能力**。
- 只改手写段落，未触碰 `<!-- BEGIN/END GENERATED -->` 区块；`generate_command_docs.py --check` 仍通过。

### 命令清单改为单一数据源生成（2026-09-19）

同一份"命令事实"原先手工维护在 `SKILL.md`、`protocol.md` 和两份 README 里，漂移反复发生（9-18 刚做过一次大同步）。现改为：

- **`skill/references/command-registry.json`** —— 单一数据源。58 条命令，每条带 `action` / `command` / `cli` / `args` / `tier` / `purpose` / `protocol_purpose` / `blocks`。
- **`scripts/generate_command_docs.py`** —— 生成器（`--check` 为校验模式，漂移时 exit 1）。只替换 `<!-- BEGIN/END GENERATED: <id> -->` 之间的表格，手写段落（决策树、红线、注意事项）一律不动；零第三方依赖；保留文件原行尾。
- 四个生成区：`skill-action-map`、`skill-additional`、`protocol-actions`、`protocol-additional`。
- `command` 是协议形式（无 `--session`），`cli` 是 SKILL.md 的 CLI 形式，两者不同源是因为两份文档的意图不同——一个讲"怎么敲命令"，一个讲"协议长什么样"，单字段无法同时表达。
- **`tests/test_command_registry.py`**（14 例）：registry schema 校验、action 唯一、每个区块有归属、非法 registry 被拒、生成幂等、CRLF/LF 保留、标记缺失报错、`--check` 能发现漂移且还原后转绿。
- `AGENTS.md` 新增「Changing a command」流程说明。
- 全量测试 **306 passed / 1 skipped**（原 292，无回归）。

## [Unreleased]

### Synced `bsk browsers close` and refreshed the READMEs (2026-09-18)

`browserskill-new` gained a `browser.close` RPC (`1628377` → `013e017`, 2026-09-17) — the first command that reaches outside a session. Pro now documents it, and the two READMEs were brought up to the 0.2.3 world.

- **SKILL.md**: `bsk browsers close` added to the fork-build tier of the version block and to the capability list, with the rules that matter: exact `instance_id` only, mandatory `--confirm`, it closes every window of that instance, it is not cleanup (`session stop` is), and success is `disconnected: true` — a timeout means the browser is still running.
- **references/user-tab-control.md**: new "Closing a browser instance" section (flags, confirmation, success/failure semantics, and the `unknown_method` fallback on a 0.2.3 extension). Intro now covers both the 2026-09-14 tab work and the 2026-09-17 close work.
- **README.md / README_ZH.md**: both still described 1.0.0. Added a **版本兼容 / Version compatibility** table (bsk CLI & extension 0.2.3, daemon protocol 1.3, Python 3.8+, Node/pnpm for source builds) and the three-tier capability table (0.2.3 / 0.2.4+ / fork build); rewrote the feature table around `observe`-first, upload/download, record + replay, health/fallback and instance-level operations; quick start now covers the fork install URL, `bsk --version` parity, `bsk doctor`, and `bsk install-skill --list|--all|--source`; new usage examples (observe, record/replay, network/console, upload/download, full-page screenshot, health_checker/fallback_chain, user tabs + `browsers close`); project tree lists every script; known limits gain the tiering, protocol-gate, idle-timeout, rich-text and close-instance rows; roadmap now reads v1.1.0 shipped / v1.2.0 planned.
- **protocol.md**: `browsers close` row added to the Additional BrowserSkill Actions table (fork build; success is `disconnected: true`).
- **CHANGELOG.md**: added the missing **[1.1.0] - 2026-09-17** entry (0.2.3 alignment, capability tiers, six new reference docs, `health_checker.py` + `fallback_chain.py`, deprecations, 292 tests, compatibility matrix) plus this Unreleased section and the version-history / link rows.

### Aligned with bsk CLI 0.2.3 + post-0.2.3 additions (2026-09-17)

Synced against `browserskill-new` HEAD (`abfea72`, 2026-09-14), which merges Tencent/BrowserSkill through PR #226 / #225 / #237 / #220 / #217 / #211 / #209 / #205 / #224 / #223 plus the fork's own user-scope tab work. Baseline is the 0.2.3 release (2026-09-08); the rest is unreleased.

#### Tier labels

Every command now carries its availability tier, instead of implying one version supports everything:

- Released baseline: **bsk CLI / extension 0.2.3**, daemon protocol 1.3.
- **0.2.4+** — merged after the 0.2.3 tag (build newer than 2026-09-08): `screenshot --full-page`, `wheel`, `scroll-to`, `focus` / `blur`, `session start --name` with operation audit, and the extension automation settings that replace `--unattended`.
- **Fork build only** — `tab list|create|select --browser-id` and `tab observe` (`916938/zenx-bridge` @ 2026-09-14+).

#### New reference documents (ported from upstream `docs/`, adapted)

- `references/long-screenshot.md` — full-page capture contract: `--full-page` vs `--ref` exclusivity, 2-minute default deadline raised with `--timeout`, atomic write after the whole byte count validates, no partial-success failures, supported-page limits, OPFS staging and release rules, version-match requirement.
- `references/wheel.md` — native mouse-wheel input: delta/modifier/target rules, viewport-centre fallback, why success means "dispatched" rather than "scrolled", CSS-pixel and page-zoom caveats, error codes.
- `references/scroll-to.md` — element reveal contract: returned `x/y/width/height` in top-level viewport CSS pixels, partial visibility counting as success, the rectangle not being an occlusion test, full error table.
- `references/operation-audit.md` — one session = one task, `session start --name`, 执行中/已结束/已中断 statuses (never infer success), per-OS storage paths and `BSK_HOME` override, 30-day retention, metadata-only recording with hidden inputs.
- `references/sandboxed-agents.md` — keep the daemon in the owning host environment and connect with `BSK_HOME` + `BSK_AUTO_START=0` when a sandbox reaps child processes.
- `references/user-tab-control.md` (new, fork-only) — `--browser-id` operations and read-only `tab observe`, written from CLI source since upstream documents none of it.

#### Docs updated

- **SKILL.md**: version block rebuilt around tiers; new capability entries for full-page screenshots, `wheel` / `scroll-to` / `focus` / `blur`, `install-skill --source`, `daemon start --daemon-idle`, and the fork's user-tab commands; new **Deprecated automation overrides** section (`--unattended`, `tab borrow --no-confirm`, `BSK_REQUEST_HELP=off` parse but are ignored, and a `disabled` request-help outcome is a blocker rather than a completion signal), with the protocol gates — `request-help` needs daemon protocol 1.3, `tab borrow --timeout` needs 1.2; new **Environment variables** table including `BSK_HOME` and `BSK_AUTO_START`; a **Reference documents** index so the new files are discoverable without loading them; decision-tree entries for whole-page capture and scrolling; the user-tab workflow now reads read-only before borrowing; the task workflow tells agents to continue a truncated observation with `observe --cursor` instead of dropping to raw HTML.
- **protocol.md**: added `wheel`, `scroll_to`, `focus`, `blur` to the action table; `screenshot` row documents `full_page` / `timeout`; new **Reading large or canvas-heavy pages** section (`observe --cursor` continuation contract, `truncated` / `next_cursor`, canvas regions exposed as `@eN` refs and capturable with `screenshot --ref`); new **Scrolling and viewport**, **Full-page screenshots**, **User-scope tabs** and **Daemon location and startup** sections; the long-page recipe prefers `scroll-to` / `wheel` and demotes the `evaluate` form to a fallback for older builds.
- **operations.md**: dependency table and version-matching block moved to 0.2.3 with the unreleased tiers named; `install-skill --source` documented as the durable install that auto-sync protects; five new diagnose rows (protocol-gate failures, `BSK_AUTO_START=0`, daemon reaped by a sandbox, immediate full-page failure, deprecated automation overrides); new **Sandboxed Agent commands** section.
- **examples/**: new `long_screenshot.md` (capture → verify → clean up, plus the staggered fallback) and `user_tab_and_scroll.md` (read-only identity check, borrow only to act, scroll, return); `scroll_and_extract.md` now leads with `wheel` / `scroll-to`.

#### Scripts

- `screenshot.py`: `--full-page` and `--timeout` (seconds) forward `--full-page` / `--timeout <n>s` to `bsk screenshot`; `--selector` + `--full-page` is rejected before any daemon call; `--timeout` is forwarded only for full-page captures.
- `screenshot.ps1`: matching `-FullPage` switch and `-TimeoutSec` wiring, keeping Python/PowerShell parity.
- `bsk_client.py`: `True` keyword values emit a bare flag (`full-page=True` → `--full-page`) instead of a value-taking pair, for both `bsk()` and `bsk_with_raw()`.
- `tests/test_screenshot.py`: 5 new cases (flag default, parsing, mutual exclusion, forwarded flags, viewport calls omitting `--timeout`). Suite: 292 passing.

### v1.1.0 P0 completion: health monitoring + fallback chain (2026-09-08)

- `health_checker.py` (roadmap #3) — session health monitoring: environment checks (daemon reachability, connected browsers, version skew, recent restart, daemon latency) plus session-level checks (liveness, tab-list readability, zombie sessions with zero tabs). Emits a JSON `HealthReport` (`healthy` / `degraded` / `unhealthy`) with per-issue severity/category, `SessionMetrics`, recovery suggestions, and `--auto` recovery for auto-recoverable issues. Probes are injectable for testing; environment-level problems point back to `doctor.py`.
- `fallback_chain.py` (roadmap #4) — graceful degradation: passthrough (`bsk invoke`) → legacy (typed subcommands) → simplified (optional args stripped) levels with an extensible `LevelSpec` registry, `--fallback enabled|disabled` / `--max-fallback-depth` config, per-attempt decision logging (mode, status, error, duration, next action), error-category escalation rules (TRANSIENT/SYSTEM/param errors fall through; other PERMANENT/USER_ERROR stop), and an emergency-cleanup hook on SYSTEM-class exhaustion.
- `tests/test_health_checker.py` (17 cases) and `tests/test_fallback_chain.py` (22 cases).
- Docs: `operations.md` gained a "Session health checks" section; `SKILL.md` helper guidance mentions `health_checker.py`; README features and roadmap status updated.

### Aligned with bsk CLI 0.2.2 (2026-09-08)

- **SKILL.md**: recommended versions updated from bsk CLI 0.1.7 / extension 0.1.3 to **0.2.2** (CLI / Extension / DSH Plugin share one semver since 0.2.2), with a feature-availability-by-CLI-version table (0.2.0 invoke / 0.2.1 observe+hover+emulate+templates / 0.2.2 upload+download+probe-hover+fill validation).
- **SKILL.md**: `bsk observe` (VOM semantic view) added to the quick action map as the preferred first observation; reading escalation chain `observe → --probe-hover → snapshot → get-html → screenshot` documented in the decision tree and task workflow; `hover` action documented; new "Recover from fill errors" section (`fill_value_mismatch`, `fill_target_changed`, `target_not_fillable`).
- **SKILL.md**: `request-help` outcome updated to 0.2.2 semantics (`continued`, `completed`, `cancelled`, `timed_out`, `disabled`; `navigated` deprecated). Smart label semantics documented: `instance_id` is the stable routing key, labels are editable aliases that may be duplicated and must not be cached across tasks. `bsk session start --no-focus` documented.
- **SKILL.md / protocol.md**: new commands documented — `console`, `upload` (`--mode input|drop`, repeatable `--file`), `download` (`--overwrite`), `emulate --device` (new tabs do not inherit; `--off` restores), `window resize`, `templates` (metadata CRUD, never a credential backup), `logs`, `update`, `completion`.
- **protocol.md**: new "File transfer (bsk 0.2.2+)" section with the upload decision sequence (input mode → `file_input_not_activated` + `effect_state=none` → one `--mode drop` attempt → `request-help`; never repeat when `effect_state` is `unknown`/`committed`).
- **operations.md**: runtime dependency table, CLI verification comment, and version-matching section updated to 0.2.2.
- **README.md / README_ZH.md**: version badge → v1.1.0; roadmap section updated to reflect the v1.1.0 MVR shipped state and remaining P0 items.

### v1.1.0 MVR infrastructure modules (2026-07-17)

- `error_codes.py` — error classification (TRANSIENT / PERMANENT / SYSTEM / USER_ERROR), 14 predefined codes with retryability metadata.
- `error_formatter.py` — JSON error/success envelopes with UUID tracking, timestamps, suggestions, and recovery actions.
- `validator.py` — fail-fast input validation: XSS/SQL injection patterns, field validators (session_id, URL, selectors, filenames), path traversal protection.
- `retry_handler.py` — exponential backoff with ±20% jitter, transient-only retries, configurable strategies, decorator support.
- `timeout_manager.py` — 4-layer timeout architecture (10s/30s/300s/600s), SIGINT/SIGTERM graceful cancellation, cooperative cancellation tokens.
- 7 new test modules (+217 tests; 238 total passing at release).

### Synced from BrowserSkill upstream (2026-07-23)

- **New helpers for `bsk record` and `bsk network`** (upstream CLI 0.1.8):
  - `record.sh` / `record.ps1` wrap `bsk record start|stop`. `start` opens the Agent Window and blocks until the user clicks Finish, writing `trace.json`. Optional `--browser`, `--url`, `--purpose`, `--output` flags mirror the upstream CLI.
  - `network.sh` / `network.ps1` wrap `bsk network`. Cursor-paginated (`--since` → `next_since`), with `--limit`, `--max-text-chars`, and `--tab-id` passthrough. Useful for XHR / fetch traffic inspection without falling back to `evaluate + fetch` reflection.
- **`replay.py`** — new script to execute a `bsk record` trace against an active session. This closes the gap upstream leaves open by design (there is no `bsk replay`):
  - Takes a fresh snapshot before every interactive step and matches each step's semantic `TargetDescriptor` (role + name) to an `@eN` ref using a scored matcher.
  - **Red-line hard stops**: `redacted:true` `fill` steps refuse to execute (never types password placeholders); ambiguous or no-match targets error out instead of grabbing a same-role sibling; unknown ops halt replay.
  - `--dry-run` prints the resolved bsk commands without executing them (still calls `bsk snapshot` for target resolution).
  - `--from-step N` resumes after a failure.
  - `click` steps with `effect.navigated_to` automatically trigger `bsk wait-for-navigation` before the next step.
- **`BSK_DEFAULT_SESSION` env-var fallback** in `invoke.sh` / `invoke.ps1`: when `--session` / `-Session` is omitted, the helpers pick up `$BSK_DEFAULT_SESSION` (validated with the same character-class rule as an explicit flag). Explicit CLI arg still wins. Lets a long-lived session be pinned once per shell instead of threaded through every call.
- **`--dry-run` passthrough** in the `bsk invoke` branch of both helpers: `--dry-run` now appends `--dry-run` to the built `bsk invoke` command and actually runs it, so the daemon can validate action name, JSON schema, and session existence. The command line is printed to stderr so callers still see what would run, and stdout stays clean for piping. The legacy typed-subcommand fallback branch keeps the old echo-and-return behavior since those subcommands don't support `--dry-run`.
- **SKILL.md**: documented the three new helper groups. "Recording and replay" section covers `record.sh` / `replay.py`, the semantic target → `@eN` matching contract, the redacted-fill hard stop, and `--dry-run` / `--from-step` usage. "Network inspection" section covers the cursor-paginated `network.sh` / `network.ps1`. Two new lines added to the "Additional BrowserSkill capabilities" list so agents discover `bsk record` and `bsk network` at scan time.

### Synced from BrowserSkill upstream (2026-07-17)

- **SKILL.md**: Added comprehensive **"Dual-mode execution"** documentation section (8 subsections):
  - **Mode comparison table**: Side-by-side comparison of passthrough vs legacy across 11 dimensions (version requirements, JSON handling, Unicode support, host-side dependencies, action resolution, error messages, performance)
  - **Auto-detection workflow**: ASCII flowchart showing runtime detection logic (`bsk invoke --help` check → mode selection → command construction)
  - **When each mode is used**:
    - Passthrough: complex nested args, Unicode text, large payloads (>1KB), production environments
    - Legacy: simple flat args, older bsk versions, basic workflows
  - **Legacy mode limitations**: Documented 4 known limitations with workarounds (nested objects, arrays, Chinese text, unmapped actions)
  - **Code examples for both modes**:
    - Passthrough: Complex nested JSON with options object, PowerShell hashtable with nested structure
    - Legacy: Simple URL navigation, flat fill command, snapshot call
  - **Advanced forcing methods**: Direct `bsk invoke` calls and `BSK_SKIP_INVOKE` env var (with deprecation note)
  - **Mode verification commands**: Bash/PowerShell one-liners to check active mode and test helper output
  - **Upgrade guide**: 4-step migration path from legacy to passthrough (check version → upgrade bsk CLI → verify → no config changes needed)
  - **Agent developer notes**: Migration guidance, testing recommendations, future-proofing tips, new feature targeting strategy
- **SKILL.md**: Added version compatibility section:
  - Documented bsk CLI 0.1.0+ requirement and recommended versions (CLI 0.1.7, Extension 0.1.3)
  - Explained `bsk invoke` passthrough command (available in bsk 0.2.0+) benefits
  - Updated Quick action map with auto-detection behavior explanation
  - Enhanced Use helpers section with runtime detection details
- **invoke.sh / invoke.ps1**: Implemented **backward-compatible `bsk invoke` auto-detection**:
  - **Passthrough mode** (preferred, bsk 0.2.0+): Forwards raw JSON via `bsk invoke --action <name> --args-json <json>`; no host-side JSON parsing required
  - **Legacy mode** (fallback, bsk < 0.2.0): Maps action names to specific typed bsk commands (`fill` → `bsk fill`, `tab_list` → `bsk tab list`, etc.)
  - Auto-detection via `bsk invoke --help` at script invocation time (zero-config)
  - Legacy mode supports 20+ actions: navigate, tab_create, tab_list, snapshot, click, fill, evaluate, screenshot, tab_close, session_stop, press, select, navigate-back, navigate-forward, reload, request-help, get-html, wait-for-navigation, wait-ms, tab_select
  - Complex/nested JSON works reliably in passthrough mode; legacy mode has limitations but covers common use cases
  - Both scripts maintain identical feature parity: --force guards, session validation, timeout handling, dry-run support
- **operations.md**: Added comprehensive **"Development environment setup"** section with:
  - **Runtime dependencies table**: Python 3.8+ (recommended 3.10+/3.12+), PowerShell 5.1+/7+, Bash, bsk CLI 0.1.7, Extension 0.1.3, Git 2.20+
  - **Python environment verification**: Windows (`py -3`) vs POSIX (`python3`) commands; confirms zero external dependencies (standard library only)
  - **PowerShell environment check**: Version detection, language parser availability
  - **bsk CLI verification**: `bsk --version`, `bsk status`, `bsk doctor` connectivity tests
  - **Browser/extension validation**: `bsk browsers`, extension connection status
  - **Development tools for contributors** (optional): IDE recommendations, ShellCheck for Bash linting
  - **Platform-specific notes**:
    - Windows: `py -3` launcher, PowerShell paths, Git Bash behavior, temp directory location
    - macOS: Xcode command-line tools, Homebrew option, python3 vs python distinction
    - Linux: Debian/Ubuntu package requirements, bash availability
  - Positioned between Status routing and Building sections for logical flow
- **operations.md**: Enhanced "Building the extension from source" section with:
  - Structured subsections: Prerequisites, Build steps, Load in Chrome, Development with hot reload, Version matching, Troubleshooting builds
  - **Updated dependency version information**:
    - Added version requirements table: Node.js 18+, pnpm 10.17.0 (pinned), Rust 1.85+ (edition 2024)
    - Added prerequisite verification commands (`node --version`, `pnpm --version`, `rustc --version`, `bsk --version`)
    - Documented pnpm pinning policy and lockfile integrity requirements
    - Noted Rust edition 2024 specifics and component requirements (rustfmt, clippy)
  - **Enhanced version matching section**:
    - Added current versions: CLI 0.1.7, Extension 0.1.3 (as of 2026-07-16)
    - Documented protocol schema location and commit policy
    - Explained version skew consequences and CI verification
  - **Expanded troubleshooting table** (6 → 11 entries):
    - Added Node.js/Rust/pnpm version-specific issues
    - Added Cargo lockfile, Biome, WXT, schema regeneration failures
    - Included exit code 5 protocol mismatch diagnosis
    - Linked to specific fix commands for each issue
  - **Added build command reference section**:
    - Full CI-equivalent build sequence (format → lint → test → compile → build)
    - Quick iteration commands for development
    - Documented `wxt prepare` requirement before TypeScript checks
  - Removed duplicate "Building the extension from source" section that existed later in the file
- **operations.md**: Restructured "Installation" section with:
  - Three-step installation flow: CLI → Extension → Pro skill package
  - Added `bsk --version` verification step
  - Added Chrome Web Store extension installation link
  - Documented `bsk install-skill` command for automatic harness installation (with `--list`, `-H`, `--all`, `-y` options)
  - Added Option A (automatic) vs Option B (manual) installation paths
  - Integrated Post-install verification into Installation section (removed duplicate standalone section)
  - Clarified installation paths (~/.local/bin) and platform-specific notes
- **README.md**: Added link from extension build instructions to the detailed operations.md section
- Verified all 21 unit tests pass after sync.
- Confirmed SKILL.md already contains equivalent or more detailed versions of upstream additions (quick decision tree, feature comparison table, multi-browser support).

### Fixed

- `invoke.sh` no longer silently drops all action arguments when `jq` is absent. The helpers no longer parse or flatten JSON at all — see the passthrough rework below — so the `jq` dependency (and the silent-drop failure mode) is gone entirely.
- Action names in examples and reference tables now use bsk protocol vocabulary (`tab_list`, `tab_close`, `session_stop`) instead of friendly names (`find_tab`, `list_tabs`, `close_session`) that resolved to non-existent `bsk` commands (e.g. `find_tab` → `bsk find tab`) and never actually ran.
- The `find_tab`-with-URL recipe was corrected: no server-side URL filter exists (`tool.tab_list` accepts only `scope` + `session_id`), so the docs now show `tab_list --scope user` followed by client-side URL/title matching instead of implying a server-side filter.

### Added

- `bsk invoke` passthrough subcommand (in the bsk CLI at `H:\skills\BrowserSkill`): forwards a raw JSON params object to any `tool.*`/`session.*` RPC, resolving bare (`fill`) or qualified (`tool.fill`) action names to protocol methods. This lets the shell helpers stop flattening JSON into typed flags.
- `invoke.sh` / `invoke.ps1` are now thin passthroughs to `bsk invoke` — they validate a few flags, translate `--timeout` seconds to `--timeout-ms`, and forward the JSON blob (`--args-json`, `--args-file`, or stdin) verbatim. No host-side `jq`/`python3` JSON handling remains.
- `--force` / `-Force` guards on both helpers cover every spelling that resolves to a session-stopping method (`session_stop`, `session_stop_all`, `session.stop`, `session.stop_all`, plus the legacy `close_session`), so the gate cannot be bypassed via an alternate form.
- `invoke.sh --args-stdin` and `--args-file -` to read UTF-8 JSON from stdin, avoiding temporary files for non-ASCII or complex arguments.
- Interactive terminal guard: `invoke.sh --args-stdin` refuses to wait on an interactive terminal.
- Rich-text editor guidance in SKILL.md and protocol.md: `fill` on `contenteditable` is plain-text replacement, does not preserve formatting.
- Shell boundary clarity: explicitly match `invoke.ps1` to PowerShell and `invoke.sh` to Bash.
- BrowserSkill-specific commands: `bsk press`, `bsk select`, `bsk navigate-back`, `bsk navigate-forward`, `bsk reload`, `bsk request-help`, `bsk get-html`, `bsk wait-for-navigation`, `bsk wait-ms`.
- Session management via `bsk session start` / `bsk session stop`.
- Tab borrowing/returning via `bsk tab borrow` / `bsk tab return`.
- Multi-browser support: `bsk browsers` lists connected instances, `--browser <id-or-label>` targets a specific browser.
- `bsk tab select` for focusing agent tabs (documented in recovery flow and action tables).
- `bsk status` for connection health diagnostics.
- `bsk session list` for listing active sessions.
- `bsk session stop --all` for emergency cleanup.
- `bsk reload --hard` flag to bypass browser cache.
- Session idle timeout warning (5 minutes) in SKILL.md and operations.md.
- Exit code table (0–5) in protocol.md with meaning and recommended action.
- Global flags table (`--json`, `--quiet`, `-v`/`-vv`) in protocol.md.
- `request-help` parameter details (`--prompt`, `--target`, `--title`, `--timeout`) and outcome types in SKILL.md.
- "When NOT to use" section in SKILL.md with usage boundary constraints.
- Extension build-from-source instructions for `apps/extension/dist/chrome-mv3` unpacked load.
- `system.ping` keepalive heartbeat documented in protocol and how-it-works.
- `screenshot --ref @eN` element crop example in protocol.md.
- Multi-browser architecture explanation in how-it-works.md.

### Changed

- Migrated from Kimi WebBridge to Tencent BrowserSkill.
- Replaced `webbridge_client.py` with `bsk_client.py` — a subprocess-based CLI wrapper for the `bsk` command.
- Updated `doctor.py` to use `bsk doctor --json` instead of HTTP-based daemon status checks.
- Updated `snapshot.py`, `screenshot.py`, and `wait_for.py` to use `bsk` CLI instead of HTTP POST.
- Updated `invoke.ps1` and `invoke.sh` to use `bsk` CLI instead of HTTP POST to daemon.
- Updated `SKILL.md`, `protocol.md`, `operations.md`, and `how-it-works.md` for BrowserSkill.
- Updated `openai.yaml` with new skill name and prompt.
- Updated README.md with BrowserSkill installation and usage instructions.
- Updated unit tests to work with new `bsk_client.py` module.
- README installation section now recommends `install.sh` / `install.ps1` installer scripts as primary method, with `cargo install` as alternative.
- Version skew (exit code 5) failure entry added to operations.md diagnose table.

### Fixed

- Removed `webbridge_client.py` and `test_mock_daemon.py` (HTTP-based mock daemon tests no longer applicable).
- Fixed duplicate `## 隐私与安全` header in README.md.
- Fixed step numbering in README: extension install is step 2, skill install is step 3.

### Validation

- All unit tests pass: `python -m unittest discover -s tests -v`

## v1.0.0 — 2026-06-20

First formal release of ZenX Bridge Skill as an agent-neutral browser-control skill.

### Added

- PowerShell `invoke.ps1 -ArgsFile` support for UTF-8 JSON argument files, including Chinese text and nested action arguments.
- `snapshot.py --auto` and `--mode auto`, which return compact snapshots for small pages and write large or overfull snapshots to a UTF-8 JSON file.
- Top-level `reason` in `doctor.py` readiness output, plus a `--json` compatibility flag for agents that explicitly request JSON output.
- A quick decision tree in `SKILL.md` for choosing tab ownership, snapshot strategy, argument passing, and post-click recovery flow.
- End-to-end examples under `skill/examples/` for form filling, long-page extraction, popup/background-tab recovery, and network debugging.

### Changed

- Updated protocol and operations guidance to prefer `wait_for.py` plus a fresh snapshot after navigation or state-changing clicks.
- Clarified when to use `snapshot.py --auto`, `--mode compact`, and `--mode file`.
- Documented UTF-8 args-file workflows for both PowerShell and Bash.
- Updated README feature and project-structure sections to reflect the helper and examples layout.

### Validation

- Unit tests: `py -3 -m unittest discover -s tests -v`
- Python script compilation for `skill/scripts/*.py`
- PowerShell parser checks for `skill/scripts/*.ps1`
- Git Bash syntax check for `skill/scripts/invoke.sh`
- `git diff --check`
- `skill-creator` quick validation for `skill/`
- Manual PowerShell dry-run for `invoke.ps1 -ArgsFile` with Chinese and nested JSON

### Deferred

- Daemon-side automatic tab switching after clicks remains outside this skill repository.
- Stitched full-page screenshots are deferred until there is a stable screenshot/scroll contract and an explicit image dependency decision.
