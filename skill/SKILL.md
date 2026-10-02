---
name: zenx-bridge-skill
description: "Control the user's real logged-in browser through the local BrowserSkill daemon. Use when the task requires a real browser session, login state, existing tabs, screenshots, form filling, confirmed file uploads, PDF saving, or network diagnosis. Prefer a dedicated API, MCP tool, or site-specific skill when one is explicitly available and sufficient. Do not use for pure web search, factual lookup, or tasks that do not need browser state."
---

# ZenX Bridge Skill

Control the user's live browser through the bsk CLI.

**Version compatibility**: This skill package works with **bsk CLI 0.1.0+**. The **`bsk invoke` passthrough command** (available in bsk 0.2.0+) enables the invoke helpers to forward raw JSON without host-side parsing. If `bsk invoke` is unavailable, helpers automatically fall back to direct typed-command mode.

**Requires the fork build** — `916938/zenx-bridge`, not upstream `Tencent/BrowserSkill`. Several commands below
(`browsers close`, `--browser-id` tab management, `tab observe`, `invoke`, `templates`, `completion`) exist only in the
fork. The fork keeps its own version line, numbered above the upstream release it last synced (upstream 0.3.0 → fork 0.4.0).

Current recommended versions:
- **bsk CLI**: 0.4.0 (fork build)
- **BrowserSkill extension**: 0.4.0 (fork build; CLI / Extension / DSH Plugin share one semver since 0.2.2)
- **Daemon protocol**: 1.3

Feature availability by CLI version:

- `bsk invoke` passthrough: 0.2.0+
- `bsk observe` (VOM semantic view), `hover`, `console`, `emulate`, `window resize`, `templates`, `logs`, `update`, `completion`: 0.2.1+
- `bsk upload` / `bsk download`, `observe --probe-hover`, fill validation errors: 0.2.2+
- `bsk screenshot --full-page`, `bsk wheel`, `bsk scroll-to`, `bsk focus` / `bsk blur`, extension automation settings replacing CLI overrides, `session start --name` with operation audit: **0.2.4+** (merged after the 0.2.3 release; requires a build newer than 2026-09-08)
- User-scope tab commands (`tab list|select|create --browser-id`, `tab observe`): **fork build only** (`916938/zenx-bridge` @ 2026-09-14 or later)
- `bsk browsers close` (quit a whole browser instance): **fork build only** (`916938/zenx-bridge` @ 2026-09-17 or later)
- `--since last_action` cursor, profile account id reporting, instance smart labels: **fork build only** (2026-09-19 or later)

A command in the 0.2.4+/fork tiers is absent from released binaries. Confirm with `bsk <command> --help` before relying on it, and continue with what the installed build supports when it is missing. The fork's remote/server mode is carried in the tree but unsupported — never treat it as an available capability.

## When NOT to use

- Tasks with **no browser** involved (files, APIs, databases only)
- Installing or configuring the extension (point the user to setup docs instead)
- **Credential harvesting** — never run `bsk evaluate` on banking, SSO, or password-manager pages to extract tokens, cookies, or secrets
- Long-lived control of a user's personal login window — borrow only for the immediate step, then `bsk tab return` or end the session
- Replacing the user's manual browsing when they only wanted an explanation

## Before every task

1. Check readiness without sending browser actions:

   ```powershell
   py -3 scripts\doctor.py --wait-connected 20
   ```

   ```bash
   python3 scripts/doctor.py --wait-connected 20
   ```

   Proceed only when the report has `"ready": true`. Otherwise run `bsk doctor` for detailed diagnosis.
2. Start a BrowserSkill session and capture the session ID:
   ```powershell
   $sessionId = bsk session start
   ```
   If multiple browsers are connected, specify which one:
   ```powershell
   $sessionId = bsk session start --browser <instance-id-or-label>
   ```
   Run `bsk browsers` to list available instances. Use `--browser-id <instance-id>` when the routing key must never resolve through a label. Add `--no-focus` to the same start command when the Agent Window should not interrupt the user's current work. `--name "..."` labels the session in local operation audit (0.2.4+).
3. Use `bsk tab list --scope user` + `bsk tab borrow <tab-id>` for user-owned existing tabs, or `bsk navigate <url>` for task-owned tabs.

**Smart labels are editable aliases, not identity.** The `instance_id` is the stable routing key; a label may be duplicated, missing, or offline. When a label is ambiguous, re-run `bsk browsers` and use the full `instance_id` instead of guessing. Labels are edited in the extension popup and may briefly reconnect the extension — never cache label-to-id mappings across tasks. Do not switch an active session to another instance; stop it and start a new one.

**Session idle timeout is 5 minutes.** Do not rely on idle timeout for cleanup — always call `bsk session stop <id>` explicitly when done, even on error paths. Emergency cleanup: `bsk session stop --all`.

## Quick decision tree

- Need the user's existing login state or current tab? Use `bsk tab list --scope user` to find the tab, then `bsk tab borrow <tab-id>`, then take a snapshot.
- Need an isolated tab you can close later? Use `bsk navigate <url>` in the Agent Window.
- Multiple browsers connected? Run `bsk browsers` to list them, then `bsk session start --browser <instance-id-or-label>` to target a specific one.
- Page state is unknown? Start with `bsk observe --session <id>` — a semantic VOM view with fresh `@e` refs. Use `snapshot.py --auto` only when a stricter static accessibility tree is more useful.
- Expected control is missing and no `[has-submenu]` / `[hover first: ...]` marker points at a trigger? Try `bsk observe --probe-hover` once (0.2.2+), or hover the trigger with `bsk hover <ref>` and observe again before acting.
- Need the whole page in one image? `bsk screenshot --full-page --out page.png --session <id>` (0.2.4+, default 2m deadline; `--timeout 5m` to extend). Exclusive with `--ref`; see [references/long-screenshot.md](references/long-screenshot.md).
- Need to scroll? `bsk scroll-to @e3` reveals one element; `bsk wheel --delta-y 600` sends native wheel input. Both are browser mutations — observe afterwards instead of assuming the scroll finished.
- Need controls only? Use `snapshot.py --mode compact`.
- Need article text, long static content, or Chinese text extraction? Use `snapshot.py --mode file` and read only the relevant file sections.
- Sending Chinese, nested JSON, or quote-heavy arguments? Use a UTF-8 args file instead of inline shell quoting.
- After `navigate` or a click that should change state? Run `wait_for.py`, then take a fresh snapshot and inspect URL/title.
- Click appears unchanged? Check `bsk tab list`, popup blocking, then recover the real link with bounded `bsk evaluate`.

## Quick action map

The `Action` column is the name you pass to the invoke helpers (`--action` / `-Action`); it maps to the `bsk` command shown next to it. The helpers auto-detect whether `bsk invoke` is available:

- **With `bsk invoke` (bsk 0.2.0+)**: Helpers forward through `bsk invoke --action <name> --args-json <json>`, which resolves action names to protocol methods (`tab_list` → `tool.tab_list`, `session_stop` → `session.stop`). This avoids host-side JSON parsing and supports complex/nested arguments reliably.
- **Without `bsk invoke` (legacy)**: Helpers fall back to calling typed `bsk <command>` subcommands directly, flattening JSON arguments into flags. This mode works but may have limitations with non-ASCII or deeply nested JSON.

<!-- BEGIN GENERATED: skill-action-map — edit skill/references/command-registry.json, then run scripts/generate_command_docs.py -->
| Action | BrowserSkill Command | Use when |
|---|---|---|
| `navigate` | `bsk navigate <url> --session <id>` | Open a URL in the selected tab. |
| `tab_create` | `bsk tab create --url <url> --session <id>` | Create a new tab in the Agent Window. |
| `tab_list` | `bsk tab list --scope <scope> --session <id>` | List tabs in scope; match a URL client-side (there is no server-side URL filter). Use `--scope user` to find user-owned tabs. |
| `observe` | `bsk observe --session <id>` | Read a semantic VOM view: URL, title, text, controls, hover surfaces, and `@e` refs. Preferred first observation. |
| `snapshot` | `bsk snapshot --session <id>` | Read a stricter static accessibility tree with `@e` refs when the semantic view is not enough. |
| `click` | `bsk click <ref-or-selector> --session <id>` | Click a snapshot ref or selector. |
| `hover` | `bsk hover <ref-or-selector> --session <id>` | Hover to reveal menus; observe again before clicking the revealed item's own ref. |
| `fill` | `bsk fill <ref-or-selector> --value <text> --session <id>` | Replace text in an input, textarea, or contenteditable field. |
| `evaluate` | `bsk evaluate <expression> --session <id>` | Read bounded page state or recover a real link. |
| `screenshot` | `bsk screenshot --ref <ref> --out <path> --session <id>` | Capture the page or an element. |
| `tab_close` | `bsk tab close <tab-id> --session <id>` | Close the selected task-owned tab. |
| `session_stop` | `bsk session stop <session-id>` | Stop the session and close all associated tabs. |
<!-- END GENERATED: skill-action-map -->

Additional BrowserSkill capabilities:
<!-- BEGIN GENERATED: skill-additional — edit skill/references/command-registry.json, then run scripts/generate_command_docs.py -->
- `bsk wheel --delta-y <px> --session <id>` - Native mouse-wheel event at the viewport centre or an optional target; `--delta-x`, `--modifiers alt,ctrl,meta,shift` (0.2.4+). Dispatch success does not mean the scroll finished.
- `bsk scroll-to <ref-or-selector> --session <id>` - Scroll an element and its frames into view; returns the visible portion's bounds in viewport CSS pixels (0.2.4+). Partial visibility counts as success.
- `bsk focus <ref-or-selector> --session <id>` - Move or drop keyboard focus explicitly (0.2.4+).
- `bsk blur <ref-or-selector> --session <id>` - Move or drop keyboard focus explicitly (0.2.4+).
- `bsk tab select <tab-id> --session <id>` - Focus an agent tab (e.g. after finding a background tab).
- `bsk status` - Connection health, connected browsers, active sessions
- `bsk browsers` - List all connected browser instances
- `bsk session start --browser <id-or-label>` - Target a specific browser when multiple are connected
- `bsk session start --browser-id <instance-id>` - Same targeting, exact instance id only; never resolves through a label
- `bsk session start --name "..."` - Label the session in local operation audit (0.2.4+; see [references/operation-audit.md](references/operation-audit.md))
- `bsk session start --no-focus` - Open the Agent Window in the background without stealing focus.
- `bsk session list` - List active sessions
- `bsk session stop --all` - Stop every active session (emergency cleanup)
- `bsk press <key> --session <id>` - Send keyboard events
- `bsk select <ref> --value <value> --session <id>` - Select dropdown options
- `bsk navigate-back --session <id>` - Browser back
- `bsk navigate-forward --session <id>` - Browser forward
- `bsk reload --session <id>` - Refresh current tab (`--hard` bypasses cache)
- `bsk request-help --session <id> --prompt "..."` - Request human intervention for CAPTCHA/login
- `bsk get-html --session <id>` - Get page HTML
- `bsk wait-for-navigation --session <id>` - Wait for navigation to complete
- `bsk wait-ms <duration>` - Wait for specified duration (no session needed)
- `bsk record start|stop --session <id>` - Record a session to trace.json for later replay (see `record.sh` / `record.ps1` helpers). There is no `bsk replay` — to redo a flow, read the trace and reuse session/observe/click/fill.
- `bsk network --session <id>` - Read buffered network responses / failures for a tab (cursor-paginated; see `network.sh` / `network.ps1`)
- `bsk console --session <id>` - Read buffered console/log/exception messages for a tab (read-only debugging)
- `bsk upload <ref> --file <path> --session <id>` - Stage a local file and attach it to the page (0.2.2+). Default input mode intercepts the native file chooser; `--mode drop` targets an explicit drop zone. Repeat `--file` for multi-file inputs.
- `bsk download <ref> --out <path> --session <id>` - Capture a browser download (0.2.2+). Default-refuses to overwrite an existing file; pass `--overwrite` when replacing is intended.
- `bsk emulate --device <preset> --session <id>` - Emulate a mobile device (viewport, UA, touch) on one tab; presets like `iphone-14`, `pixel-7`; `--off` restores the real environment. New tabs do not inherit emulation.
- `bsk window resize --width <w> --height <h> --session <id>` - Resize the session's Agent Window (100..=7680 CSS px). `bsk session start` also accepts `--width/--height`.
- `bsk observe --max-depth <n> --max-tokens <n> --session <id>` - Bound a semantic observation on a large page; the JSON result reports `truncated`.
- `bsk observe --cursor <cursor> --session <id>` - Continue a truncated observation instead of re-reading the page (0.2.4+). Use your current refs before continuing; it cannot be combined with `--max-depth`, `--probe-hover` or `--debug-surfaces`.
- `bsk screenshot --ref @eN --session <id>` - Crop to a DOM element **or a Canvas region**; canvas regions appear as `@eN` refs in `observe` (0.2.4+).
- `bsk screenshot --full-page --out <path> --session <id>` - Stitch a whole-page PNG (0.2.4+). Exclusive with `--ref`; `--timeout` sets the capture deadline (default `2m`). See [references/long-screenshot.md](references/long-screenshot.md).
- `bsk tab list --browser-id <instance-id> --scope user` - List a browser's user tabs without starting a session (fork build). Requires `--scope user`.
- `bsk tab observe --browser-id <instance-id> --tab-id <id> --expected-origin <url>` - Read visible text from a user tab read-only: no injection, no CDP, no form/storage/network access (fork build). `--expected-origin` is required and must match the tab's real origin; `--max-chars` caps output (default `4000`, max `8000`).
- `bsk tab select <tab-id> --browser-id <instance-id> [--expected-origin <url>]` - Activate a user tab and refocus its original window (fork build). Pass the origin to re-verify the tab before it is focused.
- `bsk tab create --browser-id <instance-id> <url>` - Open a tab in the user's own window instead of the Agent Window (fork build).
- `bsk browsers close --browser-id <instance-id> --confirm` - Stop every session of that instance, close all its windows, and let the browser process exit (fork build). The only command that reaches outside a session: it closes windows the agent never touched. Never use it as cleanup — `bsk session stop <id>` is cleanup. Only close an instance the user asked to close, and read `bsk browsers` first; labels and prefixes are rejected. Success is `disconnected: true` in `--json` output; a timeout means the browser is still running. There is no matching "open" command — `bsk` never starts browsers.
- `bsk install-skill --list` - Install this skill into local agent harnesses; `--list`, `--all`, `--source <path>`, `--force`; `--source` installs a custom `SKILL.md` and suspends skill auto-update.
- `bsk daemon start|stop|restart` - Manage the daemon; add `--daemon-idle 2h` or `--session-idle 10m` when starting.
- `bsk templates list|get|create|update|delete|apply` - Manage Profile Templates (metadata CRUD + controlled apply; never an account backup or credential migration mechanism).
- `bsk logs` - Print (and optionally follow) the daemon log file.
- `bsk update` - Check for and install bsk CLI updates.
- `bsk completion <shell>` - Print a tab-completion script for bash, zsh, fish, or powershell.
<!-- END GENERATED: skill-additional -->

## Use helpers

Use the bundled helper for the current shell instead of hand-escaping JSON.

The helpers (`invoke.sh` / `invoke.ps1`) **auto-detect `bsk invoke` support** at runtime:
- If `bsk invoke --help` succeeds, they use the **passthrough mode** (recommended)
- If unavailable, they fall back to **legacy direct-command mode**

This means the same helper scripts work with both old and new bsk versions without manual configuration.

## Dual-mode execution: passthrough vs legacy

The invoke helpers (`invoke.sh`, `invoke.ps1`) support **two execution modes** that are automatically selected based on the installed `bsk` CLI version:

### Mode comparison

| Feature | **Passthrough mode** (`bsk invoke`) | **Legacy mode** (direct commands) |
|---------|--------------------------------------|----------------------------------|
| **Minimum bsk version** | 0.2.0+ | 0.1.0+ |
| **JSON handling** | Raw JSON forwarded verbatim | Flattened to typed flags |
| **Complex arguments** | Full support (nested objects, arrays) | Limited (simple key-value only) |
| **Unicode/Chinese text** | Reliable (UTF-8 JSON blob) | May require workarounds |
| **Host-side dependencies** | None (no jq/python needed for args) | Requires Python for parameter extraction |
| **Action resolution** | Server-side (daemon maps names to methods) | Client-side (script maps actions to commands) |
| **Error messages** | Protocol-level detail from daemon | Command-level from CLI |
| **Performance** | Single RPC round-trip | Multiple Python invocations per call |

### How auto-detection works

At runtime, each helper script invocation checks for `bsk invoke` availability:

```
1. Script starts
   ↓
2. Run: bsk invoke --help
   ↓
3. Success? → YES  → Use PASSTHROUGH MODE
              ↓
           bsk invoke --action fill \
             --args-json '{"selector":"@e10","value":"test"}' \
             --session demo --json
   ↓
4. Success? → NO (command not found) → Use LEGACY MODE
                                   ↓
                                bsk fill @e10 --value test \
                                  --session demo --json
```

**Detection cost**: ~50ms once per script invocation (cached within single run). No configuration files or environment variables needed.

### When each mode is used

#### Passthrough mode (automatic when bsk 0.2.0+ is installed)

**Best for:**
- Complex nested arguments: `{"selector":"@e10","options":{"deeply":{"nested":true}}}`
- Unicode-heavy payloads: Chinese, Japanese, emoji, RTL text
- Large argument objects (> 1KB of JSON)
- Production environments where reliability matters
- Any workflow using `--args-stdin` or `--args-file -`

**Example usage:**

```bash
# Complex nested arguments (passthrough handles these natively)
scripts/invoke.sh --session demo --action fill --args-json '{
  "selector": "@e10",
  "value": "显卡日报 🌔",
  "options": {
    "clearFirst": true,
    "delay": 100
  }
}'
# Output: bsk invoke --action fill --args-json '{...}' --session demo --json
```

```powershell
# PowerShell with hashtable (converted to JSON automatically)
.\scripts\invoke.ps1 -Action fill `
  -Session demo `
  -ActionArgs @{
    selector = "@e10"
    value = "RTX 5090 价格 💰"
    options = @{
      clearFirst = $true
      delay = 100
    }
  }
# Output: bsk invoke --action fill --args-json '{"selector":...}' --session demo --json
```

#### Legacy mode (automatic fallback when bsk < 0.2.0)

**Best for:**
- Simple flat arguments: `{"selector":"@e10","value":"text"}`
- Environments where bsk cannot be upgraded immediately
- Development/testing on older bsk versions
- Basic workflows without complex nesting

**Known limitations in legacy mode:**

| Limitation | Workaround |
|------------|-----------|
| Nested objects not extracted | Upgrade to bsk 0.2.0+ or simplify args |
| Array parameters not supported | Use passthrough mode or manual command |
| Chinese text may need quoting | Wrap in UTF-8 file and use `--args-file` |
| Some rare action names unmapped | Use direct `bsk <command>` calls |

**Example usage:**

```bash
# Simple arguments work well in legacy mode
scripts/invoke.sh --session demo --action navigate \
  --args-json '{"url":"https://example.com"}'
# Output: bsk navigate https://example.com --session demo --json

# Fill with simple values
scripts/invoke.sh --session demo --action fill \
  --args-json '{"selector":"@e10","value":"hello world"}'
# Output: bsk fill @e10 --value hello world --session demo --json
```

```powershell
# PowerShell legacy mode
.\scripts\invoke.ps1 -Action snapshot -Session demo
# Output: bsk snapshot --session demo --json
```

### Forcing a specific mode (advanced)

In rare cases, you may want to force one mode regardless of detection:

**Force passthrough** (requires bsk 0.2.0+):
```bash
# Call bsk invoke directly, bypassing the helper's detection
bsk invoke --action fill \
  --args-json '{"selector":"@e10","value":"text"}' \
  --session demo --json --timeout-ms 30000
```

**Force legacy** (simulate old bsk behavior):
```bash
# Set an environment variable to disable invoke detection (not recommended)
BSK_SKIP_INVOKE=1 scripts/invoke.sh --action fill ...
```
> Note: The helpers are designed for auto-detection. Manual override is rarely needed and not officially supported.

### Checking which mode is active

To verify which mode your current setup uses:

```bash
# Check if bsk invoke is available
bsk invoke --help 2>&1 && echo "✅ Passthrough mode available" || echo "⚠️ Legacy mode"

# Test actual helper behavior
scripts/invoke.sh --action fill \
  --args-json '{"selector":"@e1","value":"test"}' \
  --dry-run
# Look for "bsk invoke" (passthrough) or "bsk fill" (legacy)
```

```powershell
# PowerShell check
try { $null = bsk invoke --help 2>&1; Write-Host "✅ Passthrough mode available" }
catch { Write-Host "⚠️ Legacy mode" }

# Test helper output
.\scripts\invoke.ps1 -Action fill -ActionArgs @{selector="@e1"; value="test"} -DryRun
```

### Upgrading from legacy to passthrough

If you're currently running in legacy mode and want passthrough benefits:

1. **Check current version**:
   ```bash
   bsk --version
   # If 0.1.x, you're in legacy mode
   ```

2. **Upgrade bsk CLI** (when 0.2.0+ releases):
   ```bash
   # Via install script
   curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh
   
   # Or via Cargo
   cargo install bsk-cli
   ```

3. **Verify upgrade worked**:
   ```bash
   bsk invoke --help  # Should show usage, not error
   bsk --version       # Should show 0.2.0+
   ```

4. **No other changes needed**: Your existing scripts, workflows, and configurations continue working automatically.

### Migration notes for agent developers

If you maintain agent code that calls ZenX Bridge Skill helpers:

- **No immediate action required**: Auto-detection means all existing code works on both modes
- **Recommended**: Test complex argument payloads after upgrading to ensure passthrough compatibility
- **Optional**: Add logging to capture which mode is active for debugging
  ```bash
  # In wrapper scripts
  echo "[DEBUG] Using $(bsk invoke --help >/dev/null 2>&1 && echo 'passthrough' || echo 'legacy') mode"
  ```
- **Future-proofing**: New features will target `bsk invoke` first; legacy mode receives bug fixes only

Match the helper to the shell that is actually running: use `invoke.ps1` only in PowerShell and `invoke.sh` only in Bash, including Git Bash on Windows. Do not paste PowerShell syntax such as `$env:USERPROFILE` or `& ...` into Bash.

PowerShell:

```powershell
bsk session start --session research
bsk navigate "https://example.com" --session research
```

For non-ASCII or complex PowerShell arguments, prefer a UTF-8 JSON file:

```powershell
@'
{"selector":"@e10","value":"显卡日报：RTX 5090 价格"}
'@ | Set-Content -LiteralPath .\args.json -Encoding UTF8
bsk fill "@e10" --value "显卡日报：RTX 5090 价格" --session research
```

Bash:

```bash
bsk session start --session research
bsk navigate "https://example.com" --session research
```

For non-ASCII or complex Bash arguments, stream UTF-8 JSON directly instead of creating a temporary file:

```bash
scripts/invoke.sh --session research --action fill --args-stdin <<'JSON'
{"selector":"@e10","value":"显卡日报 🌔"}
JSON
```

`--args-file PATH` remains available for reusable or generated payloads. See [protocol.md](references/protocol.md).

Use [screenshot.py](scripts/screenshot.py) for cross-platform screenshots.
For large or unknown pages, use [snapshot.py](scripts/snapshot.py) with `--auto` first. It returns compact output for small pages and writes large snapshots to a UTF-8 JSON file.
Use [doctor.py](scripts/doctor.py) for no-action readiness checks: daemon status, extension connection.
Use [health_checker.py](scripts/health_checker.py) for session-aware diagnostics when an active session misbehaves: `py -3 scripts\health_checker.py --session <id>` reports `healthy` / `degraded` / `unhealthy` with per-issue severity, metrics, and recovery suggestions. Add `--auto` to attempt recoverable fixes.
Run Python helpers with `py -3` (or `py`) on Windows and `python3` on POSIX. Do not assume `python3` is the Windows launcher.

### Recording and replay

Capture the user's own actions in the Agent Window and replay them later. Recording is an interactive user session; replay is agent-driven.

- **[record.sh](scripts/record.sh) / [record.ps1](scripts/record.ps1)** — wraps `bsk record start|stop`. `start` opens the Agent Window, blocks until the user clicks Finish, and writes `trace.json`. Use `--purpose "..."` to attach a goal string (metadata only; does not change what is captured). `stop` is a terminal fallback when the browser panel is unavailable.
- **[replay.py](scripts/replay.py)** — executes a `trace.json` against an active session. Takes a fresh snapshot before every interactive step and matches each step's semantic target (role + name) to an `@eN` ref. **Always try `--dry-run` first** — it prints the resolved commands without touching the page.

```bash
# Record
scripts/record.sh start --purpose "publish an article" --output ./flow.json

# Replay against a new session
SID=$(bsk session start)
python3 scripts/replay.py ./flow.json --session "$SID" --dry-run  # inspect plan
python3 scripts/replay.py ./flow.json --session "$SID"            # execute
bsk session stop "$SID"
```

Replay hard-stops on: redacted `fill` steps (passwords), ambiguous or missing target matches, unknown ops. Resume after a failure with `--from-step N`. Do **not** record on banking/SSO/password-manager pages — passwords are redacted, but traces may still contain sensitive text.

Full end-to-end walkthrough (record once, replay with different values): [examples/record_and_replay.md](examples/record_and_replay.md).

### Network inspection

**[network.sh](scripts/network.sh) / [network.ps1](scripts/network.ps1)** — wraps `bsk network`, returning buffered network responses/failures for a tab. Cursor-paginated: pass the previous call's `next_since` as `--since` to fetch only new entries. Prefer this over `evaluate` + `fetch` reflection when debugging XHR / fetch traffic.

```bash
scripts/network.sh --session "$SID" --limit 20 --json
# Next call: --since <cursor_from_previous_response>
```

## Deprecated automation overrides

The extension's **Automation settings** (popup → 自动化设置: 借用标签页前确认 / 允许请求人工协助) decide whether tab borrows ask for confirmation and whether human help is available. They are authoritative and saved per browser profile. These legacy inputs still parse so old scripts do not break, but they have **no effect** — the CLI only logs a warning:

| Legacy input | Use instead |
|---|---|
| `bsk session start --unattended` | Extension setting "允许请求人工协助 / Allow requests for human help" |
| `bsk tab borrow --no-confirm` | Extension setting "借用标签页前确认 / Confirm before borrowing tabs" |
| `BSK_REQUEST_HELP=off` | Same setting. A `request-help` result of `disabled` means the user turned the setting off — it is **not** a signal that they completed the step; report the blocker instead. |

Protocol-version gates: `request-help` needs daemon protocol **1.3**, and `bsk tab borrow --timeout` needs **1.2**. An older daemon fails fast with `unsupported_feature` naming the required protocol; update CLI and extension together, then `bsk daemon restart`. Everything else — sessions, navigation, reading — keeps working.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `BSK_DEFAULT_SESSION` | Session id used when `--session` is omitted | _(none)_ |
| `BSK_INVOKE_TIMEOUT_MS` | Default `bsk invoke` timeout in milliseconds | `30000` |
| `BSK_AUTO_UPDATE` | Set `off` to stop the daemon from upgrading `bsk` | on |
| `BSK_HOME` | Daemon runtime directory (`daemon.json`, sockets, audit logs) | `~/.bsk` |
| `BSK_AUTO_START` | Set `0` to disable implicit daemon startup; commands then only connect | implicit start enabled |
| `BSK_REQUEST_HELP` | **Deprecated, ignored** — use the extension automation setting | _(none)_ |

Set `BSK_HOME` on both sides when a sandboxed shell must talk to a daemon owned by the host; see [references/sandboxed-agents.md](references/sandboxed-agents.md).

## Reference documents

These are loaded on demand, not with every task:

| Document | Read when |
|---|---|
| [references/protocol.md](references/protocol.md) | Exact command parameters, exit codes, privacy constraints |
| [references/operations.md](references/operations.md) | Installation, diagnostics, recovery, shared-daemon setups |
| [references/long-screenshot.md](references/long-screenshot.md) | Full-page capture limits and failure semantics (0.2.4+) |
| [references/wheel.md](references/wheel.md), [scroll-to.md](references/scroll-to.md) | Scrolling semantics, returned bounds, error codes (0.2.4+) |
| [references/operation-audit.md](references/operation-audit.md) | What the local audit log records and where it lives (0.2.4+) |
| [references/sandboxed-agents.md](references/sandboxed-agents.md) | A sandbox reaps background daemons (shared `BSK_HOME` + `BSK_AUTO_START=0`) |
| [references/user-tab-control.md](references/user-tab-control.md) | Reading, selecting, and closing a user's browser instance without borrowing tabs (fork build) |
| [references/how-it-works.md](references/how-it-works.md) | Human maintainers: architecture and design rationale |

## Minimal workflows

Readiness smoke test, with no page changes:

```powershell
py -3 scripts\doctor.py --wait-connected 20
bsk session start
$sessionId = bsk session start
bsk tab list --session $sessionId
```

```bash
python3 scripts/doctor.py --wait-connected 20
SESSION_ID=$(bsk session start)
bsk tab list --session $SESSION_ID
```

Task-owned tab workflow:

```powershell
$sessionId = bsk session start
bsk navigate "https://example.com" --session $sessionId
py -3 scripts\screenshot.py --session $sessionId
bsk tab list --session $sessionId
bsk session stop $sessionId
```

```bash
SESSION_ID=$(bsk session start)
bsk navigate "https://example.com" --session $SESSION_ID
python3 scripts/screenshot.py --session $SESSION_ID
bsk tab list --session $SESSION_ID
bsk session stop $SESSION_ID
```

User-owned tab workflow: call `bsk tab list --scope user`, find the target tab, `bsk tab borrow <tab-id>`, take a compact `snapshot`, perform the requested action, `bsk tab return <tab-id>`, and do not close the tab unless the user explicitly asks.

If you only need to confirm which page a user tab is showing, do not borrow it: `bsk tab observe --browser-id <instance-id> --tab-id <id> --expected-origin <url>` returns the visible text read-only, with no page injection and no access to forms, storage or network (fork build). Borrow only once a real action is needed.

## Follow one task workflow

1. Start a session with `bsk session start` and capture the session ID.
2. Use `bsk tab list --scope user` + `bsk tab borrow <tab-id>` for a user-owned existing tab, or `bsk navigate <url>` for a task-owned tab.
3. Observe before acting: run `bsk observe --session <id>` for unknown pages. Escalate reading only as needed — `observe` → `observe --probe-hover` (0.2.2+) → `snapshot.py --mode compact` / `--mode file` → `get-html` → `screenshot`. Do not start with raw HTML or screenshots merely to discover ordinary controls.
   Large pages: if the observation reports `truncated`, continue it with `bsk observe --cursor <next_cursor>` (0.2.4+) or raise `--max-depth` / `--max-tokens` — do not fall back to raw HTML just because one observation was cut short.
4. Use the observation's `@e` refs with `bsk click`, `bsk fill`, `bsk hover`, and `bsk select`. Navigation invalidates refs; large DOM changes may also make them stale — observe again before the next interaction.
5. After navigation or a click that should change the page, use [wait_for.py](scripts/wait_for.py) or poll URL/title up to three times.
6. Observe again after a substantial DOM change; old refs may be stale.
7. Use `bsk tab list` before cleanup. For user-owned tabs, use `bsk tab return <tab-id>` to return them. For task-owned tabs, use `bsk session stop <id>` to close them.

Do not assume `bsk tab borrow` visibly focuses a browser tab. It selects a matching tab for the BrowserSkill session.
Treat `@e` values as BrowserSkill snapshot references, not DOM attributes. Do not query them with selectors such as `[data-ref="@e1"]`.
When using `wait_for.py`, the text condition flag is `--text-contains`; `--visible-text` is accepted as an alias.

## Recover when the page looks unchanged

**Check browser popup and new-window blocking before repeating the click.**

1. Compare the returned URL and take a fresh `snapshot`; SPA navigation may update in place.
2. Call `bsk tab list`; the destination may be in a background tab.
3. Use `bsk tab select <tab-id>` to select the destination for the session.
4. If no tab appeared, tell the user the browser may have blocked a popup or new tab. Ask them to allow popups/new windows for that site, then retry once.
5. If a result card has nested click targets, inspect its primary `href` with `bsk evaluate` and navigate directly.

## Recover from fill errors

`bsk fill` validates the result before reporting success (bsk 0.2.2+). Follow the returned error code instead of blindly repeating the fill:

- `fill_value_mismatch` — the field does not contain the exact value. Observe the field first: the page may have formatted it (currency, phone, date). Continue if the visible result satisfies the user's intent; otherwise correct the remaining difference. Do not immediately request human help.
- `fill_target_changed` — the target changed between resolution and execution. Re-observe and retry once with a fresh ref.
- `target_not_fillable` — the target is not an input, textarea, or contenteditable. Pick the real input field from a fresh observation.

## Rich-text editors

- `bsk fill` on `contenteditable` is plain-text replacement. It may remove or flatten existing markup and cannot express "bold these characters."
- Prefer the editor's accessible toolbar buttons or keyboard shortcuts when they are exposed and can be verified with a fresh snapshot.
- If neither native controls nor a safely bounded page-specific edit is available, report the formatting step as unsupported instead of claiming success.

## request-help parameters

When a step needs human intervention (captcha, login, OTP):

```powershell
bsk request-help --session <id> --prompt "Solve the captcha, then click Continue" `
  --title "Captcha required" --target @e7 --target "#submit" --timeout 5m
```

```bash
bsk request-help --session <id> --prompt "Solve the captcha, then click Continue" \
  --title "Captcha required" --target @e7 --target "#submit" --timeout 5m
```

| Parameter | Required | Description |
|---|---|---|
| `--prompt` | Yes | What the user should do |
| `--title` | No | Custom title for the overlay panel |
| `--target` | Recommended | Snapshot ref (`@e7`) or CSS selector to highlight — repeatable |
| `--timeout` | No | How long to wait (default `5m`) |

Result `outcome` (bsk 0.2.2+): `continued` (user confirmed and returned control), `completed` (user finished the step), `cancelled` (user rejected — treat as rejection), `timed_out` or `disabled` (treat as blockers, not reasons to retry), or `navigated` (deprecated — never treat navigation alone as a completion signal; refs are stale, re-observe). Resume only after `continued` or `completed`, then take a fresh `bsk observe` before using refs.

## Preserve user state

- Treat tabs borrowed with `bsk tab borrow` as user-owned. Return them with `bsk tab return` and do not close them unless the user explicitly asks.
- Treat tabs created with `bsk navigate` as task-owned. Close them via `bsk session stop` when cleanup is appropriate.
- Collect only the page content needed for the task. Treat snapshots, screenshots, PDFs, network captures, and page text as potentially sensitive.
- Do not inspect or return cookies, authorization headers, session tokens, password fields, browser storage, or unrelated private page content.
- Delete temporary screenshots and PDFs after use unless the user asked to keep them.
- Confirm before sending messages, publishing content, purchasing, deleting, changing permissions, uploading files, or submitting sensitive data.
- Do not bypass CAPTCHAs, paywalls, age gates, browser warnings, or site security controls.
- Use `bsk request-help` when encountering CAPTCHAs or login prompts that require human intervention.