# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Synced with `browserskill-new`: quit a browser — `bsk browsers close` (2026-09-18)

`916938/browserskill-new` added a `browser.close` RPC (commits `1628377` → `013e017`, 2026-09-17), the first command that reaches outside a session. It is a **fork-build capability** and does not exist in Tencent/BrowserSkill releases.

- `skill/SKILL.md` — added to the fork tier of the version block, plus a capability entry: `bsk browsers close --browser-id <instance_id> --confirm`. Documented rules: exact `instance_id` only (labels and prefixes are rejected), `--confirm` is mandatory, it closes **every** window of that instance including windows the agent never touched, it is **not** a cleanup command (`bsk session stop` is), and success is the JSON `disconnected: true` — a timeout means the browser is still running.
- `skill/references/user-tab-control.md` — new "Closing a browser instance" section with the flag table and the fallback for extensions that still answer `unknown_method: browser.close not implemented`.

#### Documentation refresh (2026-09-18)

- `README.md` / `README_ZH.md` — both READMEs still described the 1.0.0 world (bsk 0.1.7 / extension 0.1.3, "current version 1.0.0", "v1.1.0 planned"). They now carry a **版本兼容 / Version compatibility** table (bsk CLI & extension **0.2.3**, daemon protocol **1.3**, plus the 0.2.4+ and fork-build tiers), a rewritten feature table, a 0.2.3-era quick start (`bsk install-skill`, `bsk doctor`, `bsk observe`), new usage examples (`observe`, record/replay, network, upload/download, full-page screenshot, `health_checker.py`, `fallback_chain.py`), an updated project tree, and a roadmap that reflects v1.1.0 as shipped.

## [1.1.0] - 2026-09-17

Aligns the skill with **bsk CLI / extension 0.2.3** (daemon protocol 1.3) and everything merged after that tag, and completes the v1.1.0 P0 reliability work.

### Added

#### Capability tiers

Every command now carries an availability tier instead of implying one version supports everything:

| Tier | Meaning | Examples |
|---|---|---|
| **0.2.3** | Released baseline (2026-09-08) | sessions, `observe`, `snapshot`, borrow/return, `request-help`, `record`, `network` / `console`, `upload` / `download`, `emulate`, `templates` |
| **0.2.4+** | Merged after the 0.2.3 tag; needs a build newer than 2026-09-08 | `screenshot --full-page`, `wheel`, `scroll-to`, `focus` / `blur`, `session start --name` + operation audit, extension automation settings replacing `--unattended` |
| **Fork build** | `916938/browserskill-new` only, not in upstream releases | `tab list\|create\|select --browser-id`, `tab observe` (2026-09-14+), `browsers close` (2026-09-17+) |

#### New reference documents (adapted from upstream `docs/`)

- `references/long-screenshot.md` — full-page capture contract: `--full-page` vs `--ref` exclusivity, 2-minute default deadline raised with `--timeout`, atomic write, no partial-success failures, OPFS staging rules, version-match requirement.
- `references/wheel.md` — native wheel input: delta / modifier / target rules, why success means "dispatched" not "scrolled", CSS-pixel and page-zoom caveats, error codes.
- `references/scroll-to.md` — element reveal contract: returned `x/y/width/height` in viewport CSS pixels, partial visibility counts as success, the rectangle is not an occlusion test.
- `references/operation-audit.md` — one session = one task, `session start --name`, 执行中/已结束/已中断 statuses, per-OS storage paths and `BSK_HOME`, 30-day retention, metadata-only recording.
- `references/sandboxed-agents.md` — keep the daemon in the owning host and connect with `BSK_HOME` + `BSK_AUTO_START=0` when a sandbox reaps child processes.
- `references/user-tab-control.md` — `--browser-id` operations and read-only `tab observe`, written from CLI source because upstream documents none of it.

#### New helpers (v1.1.0 P0)

- `health_checker.py` (roadmap #3) — session-aware diagnostics: environment checks (daemon reachability, connected browsers, version skew, recent restart, daemon latency) plus session checks (liveness, tab-list readability, zero-tab zombies). Emits a JSON `HealthReport` (`healthy` / `degraded` / `unhealthy`) with severity, metrics and recovery suggestions; `--auto` attempts recoverable fixes.
- `fallback_chain.py` (roadmap #4) — graceful degradation passthrough → legacy → simplified, with an extensible `LevelSpec` registry, per-attempt decision logging, error-category escalation rules, and an emergency-cleanup hook.
- `tests/test_health_checker.py` (17 cases) and `tests/test_fallback_chain.py` (22 cases).

#### New examples

- `examples/long_screenshot.md` — capture → verify → clean up, plus the staggered fallback.
- `examples/user_tab_and_scroll.md` — read-only identity check, borrow only to act, scroll, return.

### Changed

- **Recommended versions**: bsk CLI / extension **0.1.7 / 0.1.3 → 0.2.3** (CLI, extension and DSH plugin share one semver since 0.2.2), daemon protocol **1.3**.
- **`bsk observe` first**: the semantic VOM view is now the default first observation; the reading escalation chain is `observe` → `observe --probe-hover` → `snapshot` → `get-html` → `screenshot`.
- **`request-help` outcomes** updated to 0.2.2 semantics (`continued`, `completed`, `cancelled`, `timed_out`, `disabled`; `navigated` deprecated).
- **New commands documented**: `console`, `upload` (`--mode input|drop`), `download` (`--overwrite`), `emulate --device`, `window resize`, `templates`, `logs`, `update`, `completion`, `install-skill --source`, `daemon start --daemon-idle`.
- **Deprecated automation overrides** section: `--unattended`, `tab borrow --no-confirm` and `BSK_REQUEST_HELP=off` still parse but do nothing; the extension's Automation settings are authoritative, and a `disabled` request-help outcome is a blocker, not a completion signal.
- **Environment variables** table added (`BSK_DEFAULT_SESSION`, `BSK_INVOKE_TIMEOUT_MS`, `BSK_AUTO_UPDATE`, `BSK_HOME`, `BSK_AUTO_START`).
- **Smart label semantics**: `instance_id` is the stable routing key; labels are editable aliases that may be duplicated and must never be cached across tasks.

### Fixed

- `screenshot.py` / `screenshot.ps1`: `--full-page` and `--timeout` are forwarded to `bsk screenshot`; `--selector` + `--full-page` is rejected before any daemon call.
- `bsk_client.py`: `True` values now emit a bare flag (`full-page=True` → `--full-page`) in both `bsk()` and `bsk_with_raw()`.
- `protocol.md` long-page recipe prefers `scroll-to` / `wheel`; the `evaluate` form is demoted to a fallback for older builds.

### Testing

- **292 tests passing** (1 skipped) — `python -m unittest discover -s tests -v`.
- 5 new `screenshot.py` cases plus 39 new P0 helper cases in this release cycle.

### Compatibility matrix

| Component | Minimum | Recommended | Status |
|-----------|---------|-------------|--------|
| bsk CLI | 0.1.0 | **0.2.3** | ✅ Supported |
| Browser extension | 0.1.0 | **0.2.3** (must match CLI) | ✅ Supported |
| Daemon protocol | 1.2 | **1.3** (`request-help` needs 1.3, `tab borrow --timeout` needs 1.2) | ✅ Supported |
| Node.js | 18+ | 20 LTS | ⚠️ Extension builds only |
| pnpm | 9.x | 10.17.0 | ⚠️ Pinned for dev |
| Rust | 1.75+ | 1.85+ / edition 2024 | ⚠️ Source builds only |
| Python | 3.8+ | 3.12+ | ✅ For helpers |

---

## [1.0.0] - 2026-07-17

### 🎉 Initial Release - Dual-Mode Execution Support

**Major Feature**: Comprehensive dual-mode execution system enabling seamless transition between `bsk invoke` passthrough mode (bsk 0.2.0+) and legacy direct-command mode (bsk 0.1.x).

### ✨ New Features

#### Dual-Mode Execution Engine
- **`invoke.sh`**: Complete rewrite with runtime auto-detection of `bsk invoke` availability
- **`invoke.ps1`**: PowerShell equivalent with identical dual-mode logic
- **Zero-config automatic fallback**: No configuration needed, selects best available mode at runtime
- **Passthrough mode** (preferred for bsk 0.2.0+):
  - Supports complex nested JSON arguments
  - Full Unicode text support
  - Handles large payloads (>1KB) efficiently
  - Production-ready with proper error handling
- **Legacy mode** (fallback for bsk 0.1.x):
  - Maps 20+ action names to typed `bsk <command>` subcommands
  - Maintains full backward compatibility
  - Simple flat argument handling for basic workflows
- **Cross-platform Python helper**:
  - Windows: Uses `py -3`
  - macOS/Linux: Uses `python3`
  - Automatic detection and validation
  - Prevents Microsoft Store redirect issues on Windows

#### Session Safety Enhancements
- **Force protection**: `session_stop`, `session_close_tab`, and similar actions require `--force` flag
- **Clear warnings**: Displays safety messages before destructive operations
- **Tab ownership verification**: Prompts user to verify task-owned tabs before closure

### 📚 Documentation Overhaul

#### SKILL.md - Comprehensive Agent Guide
Added new "Dual-mode execution: passthrough vs legacy" section (8 subsections):
- **Mode comparison table**: Side-by-side comparison across 11 dimensions
  - Version requirements
  - Command format
  - Argument complexity
  - Unicode support
  - Error reporting
  - Performance characteristics
  - Use case recommendations
- **Auto-detection workflow**: ASCII flowchart showing runtime logic
  - `bsk invoke --help` availability check
  - Graceful fallback mechanism
  - Mode selection transparency
- **When each mode is used**: Detailed examples for both modes
  - Passthrough mode scenarios with complex JSON payloads
  - Legacy mode scenarios with simple arguments
  - Decision guidance for agent developers
- **Legacy mode limitations**: Documented 4 known limitations
  - Nested objects not supported
  - Arrays require special handling
  - Chinese/Japanese text encoding issues
  - Workarounds provided for each limitation
- **Advanced forcing methods**: Expert-level configuration options
  - Direct `bsk invoke` calls
  - `BSK_SKIP_INVOKE` environment variable
  - Deprecation notices included
- **Checking active mode**: Verification commands
  - Quick status check commands
  - Debug output interpretation
- **Upgrade guide**: 4-step migration path
  - Version checking instructions
  - Testing recommendations
  - Rollback procedures
- **Migration notes for agent developers**
  - Code pattern changes
  - Backward compatibility guarantees
  - Best practices for dual-mode code

#### operations.md - Installation & Development Guide
**Restructured Installation Chapter**:
- **Step-by-step 3-step flow**:
  1. CLI installation (`bsk install-skill`)
  2. Extension setup (Chrome/Edge)
  3. Pro skill deployment
- **Post-install verification checklist**
- **Troubleshooting common issues**

**New Development Environment Setup Section** (7 subsections):
- **Runtime dependencies table**:
  - Node.js 18+
  - pnpm 10.17.0 (pinned)
  - Rust 1.85+ / edition 2024
  - Python 3.x (for helpers)
- **Python environment verification**
- **PowerShell environment requirements**
- **bsk CLI verification steps**
- **Browser/extension compatibility checks**
- **Development tools recommendations**
- **Platform-specific notes** (Windows/macOS/Linux)

**Enhanced Build Instructions**:
- **Prerequisites table** with exact version pinning
  - Node.js: 18+ (LTS recommended)
  - pnpm: 10.17.0 (exact)
  - Rust: 1.85+, edition 2024
- **Build steps** with CI-equivalent commands
- **Chrome loading instructions**
- **HMR dev server setup** (`pnpm ext:dev`)
- **Version matching requirements**:
  - CLI: 0.1.7
  - Extension: 0.1.3
  - As of: 2026-07-16
- **Troubleshooting builds table** (11 entries)
  - pnpm version mismatch
  - Rust toolchain issues
  - Node.js compatibility
  - Platform-specific solutions
- **Build command reference**:
  - Quick iteration: `pnpm ext:dev`
  - Production build: `pnpm ext:build`
  - CI equivalent commands

#### README.md - Project Overview Updates
- Added link to detailed extension build instructions in operations.md
- Updated project structure documentation
- Enhanced quick start guide
- Improved feature highlights section

#### protocol.md - Protocol Reference Updates
- Synced from upstream BrowserSkill repository
- Updated parameter definitions
- Added new command references
- Clarified error codes

### 🔧 Upstream Synchronization from BrowserSkill

**Version Pinning** (from `/h/skills/BrowserSkill` config files):
- **pnpm**: 10.17.0 (`package.json` packageManager field)
- **Rust edition**: 2024 (`Cargo.toml` workspace.edition)
- **Rust minimum version**: 1.85 (`Cargo.toml` rust-version)
- **CLI version**: 0.1.7 (workspace.version)
- **Extension version**: 0.1.3 (`apps/extension/package.json`)

**Example Workflows Updated**:
- **handle_popup.md**: Popup interaction patterns
- **login_and_fill_form.md**: Authentication + form filling workflow
- **network_debug.md**: Network debugging techniques
- **scroll_and_extract.md**: Content extraction patterns

### 🛡️ Bug Fixes & Improvements

#### Script Robustness
- **Fixed**: Empty parameter extraction in legacy mode
  - Root cause: Piping issue combined with operator precedence
  - Solution: Reusable `extract_arg()` helper function
  - Result: Reliable JSON → CLI parameter mapping
- **Fixed**: Windows `python3` Microsoft Store redirect
  - Issue: Exit code 49 on Windows Git Bash
  - Solution: Multi-fallback approach (`py` → validated `python3` → `python`)
  - Validation: Checks if Python is actual executable, not Store alias
- **Fixed**: Edit string matching failures
  - Issue: Whitespace mismatches after multiple edits
  - Solution: Exact string re-reading before each edit
  - Prevention: Unique context strings for reliable matching

#### Documentation Quality
- **Removed duplicate content** from operations.md:
  - Duplicate "Building the extension" section eliminated
  - Consolidated Post-install verification into single location
  - Clean information architecture
- **Standardized formatting**:
  - Consistent 2-space indent throughout Markdown
  - LF line endings enforced
  - Proper heading hierarchy maintained

### 🧪 Testing & Validation

#### Test Coverage
- **21 unit tests passing** (all existing + new):
  - Doctor functionality: 9 tests
    - JSON flag handling
    - Output parsing (valid/invalid JSON)
    - Readiness reason reporting
    - Deadline clamping behavior
  - Snapshot compression: 8 tests
    - Auto mode selection (compact/file-based)
    - Deep tree iteration
    - Nested list flattening
    - Element count limits
  - Wait-for arguments: 4 tests
    - Name iteration through deep trees
    - Deadline-aware polling
    - Alias mapping validation
- **Script syntax checks**:
  - Bash: `invoke.sh` passes `bash -n` validation
  - PowerShell: All `.ps1` files pass AST parsing
- **Functional dry-run testing**:
  - Legacy mode command generation verified
  - Session safety guards working correctly
  - Force flag enforcement confirmed

### 📊 Compatibility Matrix

| Component | Minimum Version | Recommended | Status |
|-----------|----------------|-------------|--------|
| bsk CLI | 0.1.0 | 0.1.7+ | ✅ Supported |
| Browser Extension | 0.1.0 | 0.1.3+ | ✅ Supported |
| Node.js | 18+ | 20 LTS | ✅ Required |
| pnpm | 9.x | 10.17.0 | ⚠️ Pinned for dev |
| Rust | 1.75+ | 1.85+/edition 2024 | ⚠️ For source builds only |
| Python | 3.8+ | 3.12+ | ✅ For helpers |

### 🚀 Migration Notes

#### For Existing Users
- **No breaking changes**: Fully backward compatible
- **Automatic upgrade**: No configuration changes required
- **Seamless transition**: Auto-detects best available mode
- **Rollback safe**: Can revert to previous version if needed

#### For Agent Developers
- **Update patterns**: Review dual-mode documentation
- **Test both modes**: Verify passthrough and legacy paths
- **Use helpers**: Prefer `invoke.sh`/`invoke.ps1` over direct `bsk` calls
- **Handle edge cases**: Check nested args, Unicode, large payloads

### 📝 Contributors
- Primary development: Based on upstream BrowserSkill improvements
- Dual-mode design: Inspired by `bsk invoke` implementation (chain branch)
- Documentation: Comprehensive rewrite for agent usability

### 🔗 Related Resources
- **Upstream repo**: https://github.com/Tencent/BrowserSkill
- **bsk invoke PR**: Implementation on `chain` branch
- **Issue tracker**: https://github.com/916938/browserskill-pro/issues

---

## Version History

### [1.1.0] - 2026-09-17
- **Release date**: September 17, 2026
- **Type**: Minor release (capability alignment + reliability)
- **Highlights**: bsk 0.2.3 / protocol 1.3 alignment, capability tiers, 6 new reference docs, `health_checker.py` + `fallback_chain.py`
- **Commit**: 004372a
- **Tag**: v1.1.0
- **Branch**: main
- **Tests**: 292 passing (1 skipped)

### [1.0.0] - 2026-07-17
- **Release date**: July 17, 2026
- **Type**: Major release (initial stable version)
- **Highlights**: Dual-mode execution, comprehensive docs, upstream sync
- **Commit**: 81c9186
- **Tag**: v1.0.0
- **Branch**: main
- **Files changed**: 26
- **Lines added**: 3,797

---

[Unreleased]: https://github.com/916938/browserskill-pro/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/916938/browserskill-pro/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/916938/browserskill-pro/releases/tag/v1.0.0
