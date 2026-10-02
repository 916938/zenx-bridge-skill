# Command Protocol

Use `bsk` CLI with JSON output:

```bash
# Start a session
bsk session start

# Navigate
bsk navigate "https://example.com" --session <session-id>

# Create new tab
bsk tab create --url "https://example.com" --session <session-id>
```

Keep `--session` and reuse one session ID for the task.

## Global flags

| Flag | Purpose |
|---|---|
| `--json` | Machine-readable JSON on stdout (errors too) |
| `--quiet` | Suppress informational stderr |
| `-v` / `-vv` | More verbose logging |

Command-specific flags: run `bsk <cmd> --help`.

## Exit codes

| Code | Meaning | Action |
|---|---|---|
| `0` | Success (including `evaluate` where JS threw but RPC succeeded) | Continue |
| `1` | User error — bad args, unknown session, tab not in Agent Window, stale ref | Fix args; `bsk session list`; re-snapshot |
| `2` | Protocol / transport — service unreachable, IPC failure | `bsk doctor`; check extension connected; retry |
| `3` | Browser / CDP execution failed | Retry; simplify selector; check tab still open |
| `4` | Timeout | Increase `--timeout`; try `--wait-until domcontentloaded` |
| `5` | Version skew (CLI vs extension) | Upgrade/reinstall matching versions |

Human errors print `error:` + `hint:` on stderr; `--json` includes `code`, `message`, `hint`, `exit_code`.

## Helper scripts

PowerShell accepts a hashtable directly:

```powershell
bsk fill "@e10" --value "显卡日报" --session demo
```

For PowerShell, use a UTF-8 JSON file when arguments contain non-ASCII text, nested objects, or complex quoting:

```powershell
@'
{
  "selector": "@e10",
  "value": "显卡日报：RTX 5090 价格"
}
'@ | Set-Content -LiteralPath .\bsk-args.json -Encoding UTF8
bsk fill "@e10" --value "显卡日报：RTX 5090 价格" --session demo
Remove-Item -LiteralPath .\bsk-args.json
```

For Bash, use a UTF-8 JSON file when arguments contain non-ASCII text or complex quoting:

```bash
printf '%s' '{"selector":"@e10","value":"显卡日报"}' > /tmp/bsk-args.json
bsk fill "@e10" --value "显卡日报" --session demo
rm -f /tmp/bsk-args.json
```

Both invoke helpers support a no-request payload check:

```powershell
& scripts\invoke.ps1 -Session demo -Action fill -ActionArgs @{
  selector = "@e10"
  value = "显卡日报"
} -DryRun
```

```bash
scripts/invoke.sh --session demo --action fill \
  --args-file /tmp/bsk-args.json --dry-run
```

Use `snapshot.py` to prevent large snapshot responses from flooding context:

```powershell
# Windows: use the Python launcher
py -3 scripts\snapshot.py --session demo --auto
py -3 scripts\snapshot.py --session demo --mode compact
py -3 scripts\snapshot.py --session demo --mode file
```

```bash
# POSIX
# Auto: compact for small pages, file path for large pages
python3 scripts/snapshot.py --session demo --auto

# URL, title, headings, and actionable refs only
python3 scripts/snapshot.py --session demo --mode compact

# Full UTF-8 response saved under the system temp directory
python3 scripts/snapshot.py --session demo --mode file
```

`auto` is the recommended first choice for unfamiliar pages: it returns compact output for small snapshots and writes large or overfull snapshots to a UTF-8 JSON file. `compact` is for locating controls. Use `file` when the task requires article text or other static page content, then read only the relevant portions of that file.
On Windows, prefer `py -3` or `py`; do not assume a `python3` command exists.
The Python helpers configure UTF-8 stdout themselves. If an older shell still renders mojibake, use `--mode file` and read the UTF-8 file instead.

Use the cross-platform screenshot helper:

```powershell
py -3 scripts\screenshot.py --session demo
```

```bash
python3 scripts/screenshot.py --session demo
```

Crop to a specific element using a snapshot ref:

```bash
bsk screenshot --ref @e3 --out /tmp/element.png --session demo
```

Wait for an expected URL, title, or visible accessibility text:

```powershell
py -3 scripts\wait_for.py --session demo `
  --url-contains "zhuanlan.zhihu.com" --timeout 10
py -3 scripts\wait_for.py --session demo `
  --text-contains "已保存" --timeout 10
```

```bash
python3 scripts/wait_for.py --session demo \
  --url-contains "zhuanlan.zhihu.com" --timeout 10
python3 scripts/wait_for.py --session demo \
  --text-contains "Saved" --timeout 10
```

`wait_for.py` accepts these condition flags:

| Flag | Meaning |
|---|---|
| `--url-contains` | Current tab URL contains the value. |
| `--title-contains` | Current tab title contains the value. |
| `--text-contains` | Accessibility tree text contains the value. |
| `--visible-text` | Alias for `--text-contains`; prefer `--text-contains` in docs. |

## Actions

The **Action** column is the name passed to `invoke.sh --action` / `invoke.ps1 -Action` (and to `bsk invoke --action`); it maps to a protocol method. The **BrowserSkill Command** column is the equivalent typed `bsk` subcommand. Both reach the same daemon RPC.

<!-- BEGIN GENERATED: protocol-actions — edit command-registry.json, then run ../../scripts/generate_command_docs.py -->
| Action | BrowserSkill Command | Arguments | Purpose |
|---|---|---|---|
| `navigate` | `bsk navigate <url>` | `url`, `wait_until`, `timeout` | Navigate the selected tab. |
| `tab_create` | `bsk tab create` | `url`, `active`, `index` | Create a new tab in the Agent Window. |
| `tab_list` | `bsk tab list` | `scope` | List tabs in scope (`user`/`agent`/`all`). No server-side URL filter; match URLs client-side. |
| `observe` | `bsk observe` | `max_depth`, `max_tokens`, `probe_hover`, `(0.2.2+)` | Read a semantic VOM view: URL, title, text, controls, hover surfaces, and `@e` refs. Preferred first observation. |
| `snapshot` | `bsk snapshot` | none | Read a stricter static accessibility tree with `@e` refs when the semantic view is not enough. |
| `click` | `bsk click <ref>` | `ref`/`selector` | Click an `@e` ref or CSS selector. |
| `hover` | `bsk hover <ref>` | `ref`/`selector`, `modifiers`, `settle` | Hover a ref/selector to reveal menus; observe again before acting on revealed items. |
| `fill` | `bsk fill <ref>` | `ref`/`selector`, `value` | Replace plain text in inputs, textareas, or contenteditable editors; rich-text markup is not preserved. |
| `evaluate` | `bsk evaluate <code>` | `expression` | Read attributes or perform unsupported page logic. |
| `screenshot` | `bsk screenshot` | `ref`, `format`, `full_page`, `timeout` | Capture the visible tab, crop to one `@eN` element with `ref`, or stitch the whole page with `full_page` (0.2.4+; see below). |
| `wheel` | `bsk wheel` | `optional ref`/`selector`, `delta_x`, `delta_y`, `modifiers`, `timeout` | Native mouse-wheel input at the viewport centre or a target (0.2.4+). |
| `scroll_to` | `bsk scroll-to` | `ref`/`selector`, `timeout` | Scroll an element and its frames into view, returning the visible bounds (0.2.4+). |
| `focus` | `bsk focus` | `ref`/`selector` | Move keyboard focus to an element (0.2.4+). |
| `blur` | `bsk blur` | `ref`/`selector` | Remove keyboard focus from an element (0.2.4+). |
| `tab_close` | `bsk tab close <tab-id>` | `tab_id` | Close the selected task-owned tab. |
| `tab_select` | `bsk tab select <tab-id>` | `tab_id` | Focus an agent tab (e.g. after finding a background tab). |
| `session_stop` | `bsk session stop <id>` | `session_id` | Close all tabs associated with the session (`--force` in the helper). |
<!-- END GENERATED: protocol-actions -->

## Additional BrowserSkill Actions

<!-- BEGIN GENERATED: protocol-additional — edit command-registry.json, then run ../../scripts/generate_command_docs.py -->
| Action | Command | Purpose |
|---|---|---|
| `status` | `bsk status` | Connection health, connected browsers, active sessions |
| `browsers` | `bsk browsers` | List all connected browser instances (id, name, version, label, sessions) |
| `session-start-browser` | `bsk session start --browser <id-or-label>` | Target a specific browser when multiple are connected |
| `session-start-browser-id` | `bsk session start --browser-id <instance-id>` | Same targeting, exact instance id only; never resolves through a label |
| `session-start-name` | `bsk session start --name "..."` | Label the session in local operation audit (0.2.4+); see [operation-audit.md](operation-audit.md) |
| `session-list` | `bsk session list` | List active sessions |
| `session-stop-all` | `bsk session stop --all` | Stop every active session (emergency cleanup) |
| `press` | `bsk press <key>` | Send keyboard events (Enter, Ctrl+A, etc.) |
| `select` | `bsk select <ref> --value <v>` | Select dropdown options |
| `navigate-back` | `bsk navigate-back` | Browser back |
| `navigate-forward` | `bsk navigate-forward` | Browser forward |
| `reload` | `bsk reload` | Refresh current tab; use `--hard` to bypass cache |
| `request-help` | `bsk request-help` | Request human intervention |
| `get-html` | `bsk get-html` | Get page HTML |
| `wait-for-navigation` | `bsk wait-for-navigation` | Wait for navigation to complete |
| `wait-ms` | `bsk wait-ms <duration>` | Wait for specified duration |
| `console` | `bsk console` | Read buffered console/log/exception messages for a tab (read-only) |
| `upload` | `bsk upload <ref> --file <path>` | Stage a local file and attach it to the page (0.2.2+); `--mode input\|drop`; repeat `--file` for multi-file inputs |
| `download` | `bsk download <ref> --out <path>` | Capture a browser download (0.2.2+); default-refuses overwrite, pass `--overwrite` to replace |
| `emulate` | `bsk emulate --device <preset>` | Emulate a mobile device (viewport, UA, touch) on one tab; `--off` restores; new tabs do not inherit |
| `window-resize` | `bsk window resize --width <w> --height <h>` | Resize the session's Agent Window (100..=7680 CSS px) |
| `browsers-tab-list` | `bsk tab list --browser-id <id> --scope user` | List a browser's user tabs without a session (fork build; `--scope user` is required) |
| `browsers-tab-observe` | `bsk tab observe --browser-id <id> --tab-id <id> --expected-origin <url>` | Read-only visible text from a user tab (fork build); see [user-tab-control.md](user-tab-control.md) |
| `browsers-tab-select` | `bsk tab select <tab-id> --browser-id <id>` | Activate a user tab and refocus its window (fork build) |
| `browsers-tab-create` | `bsk tab create <url> --browser-id <id>` | Open a tab in the user's own window instead of the Agent Window (fork build). |
| `browsers-close` | `bsk browsers close --browser-id <id> --confirm` | Stop every session of that instance and close all its windows so the browser exits (fork build). Not a cleanup command; success is `disconnected: true`. See [user-tab-control.md](user-tab-control.md) |
| `install-skill` | `bsk install-skill --harness <id>` | Install this skill into local agent harnesses; `--list`, `--all`, `--source <path>`, `--force`; `--source` installs a custom `SKILL.md` and suspends skill auto-update. |
| `daemon-start` | `bsk daemon start` | Manage the daemon directly; `--daemon-idle 2h`, `--session-idle 10m`, `--foreground` |
| `templates` | `bsk templates list\|get\|create\|update\|delete\|apply` | Profile Template metadata CRUD + controlled apply (never a credential backup mechanism) |
| `logs` | `bsk logs` | Print (and optionally follow) the daemon log file. |
| `update` | `bsk update` | Check for and install bsk CLI updates. |
| `completion` | `bsk completion <shell>` | Print tab-completion for bash, zsh, fish, or powershell |
<!-- END GENERATED: protocol-additional -->

`bsk session start` also accepts `--no-focus` (open the Agent Window without stealing focus), `--width`/`--height` (initial Agent Window size, both required together), `--browser-id <instance-id>` (exact instance routing) and `--name "..."` (operation-audit label, 0.2.4+).

## Scrolling and viewport (0.2.4+)

Prefer these two commands over `evaluate` + `window.scrollBy`; they run through the same session queue and user-interrupt gate as clicks.

```bash
# Reveal one element and read its visible bounds
bsk scroll-to @e3 --session demo --json

# Native wheel input: no target = viewport centre, positive Y scrolls down
bsk wheel --delta-y 600 --session demo
bsk wheel @e3 --delta-y -120 --modifiers ctrl,shift --session demo
```

| Aspect | `scroll-to` | `wheel` |
|---|---|---|
| Target | Exactly one (`@e3` positional, `--ref`, or `--selector`) | Optional; none means viewport centre |
| Result | `x/y/width/height` visible bounds in top-level viewport CSS px | `x/y` dispatch point plus echoed `delta_x/delta_y` |
| Partial visibility | Success (a clipped element still returns bounds) | Not applicable |
| Success means | Element is in view | The wheel event was dispatched — not that scrolling or animation finished |

Both are browser mutations: already-applied scrolling is never rolled back, so take a fresh `bsk observe` before retrying after a timeout or cancellation. Common errors: `invalid_params` (bad target/timeout), `not_found` (`ref_not_found` / `selector_not_found`), `permission_denied` (`agent_window_scope` — the tab was not borrowed, or `element_not_visible`), `cdp_failed`, `cancelled`, `timeout`. CSS selectors only search the main document; use refs for iframe and shadow-root elements. Details: [wheel.md](wheel.md) and [scroll-to.md](scroll-to.md).

## Reading large or canvas-heavy pages (0.2.4+)

`bsk observe` may return a truncated tree on very large pages. Its JSON result carries `truncated` and, when more content belongs to the same observation, `next_cursor`:

```bash
bsk observe --session demo --json                      # check truncated / next_cursor
bsk observe --session demo --cursor <next_cursor>      # continue that same observation
bsk observe --session demo --max-depth 12 --max-tokens 4000   # or raise the caps instead
```

- `--cursor` continues **one** observation: use the refs you already have before continuing, because the continuation reuses the same ref space.
- `--cursor` cannot be combined with `--max-depth`, `--probe-hover` or `--debug-surfaces` — those change what is captured. `--max-tokens` is allowed alongside it.
- `truncated: true` with no `next_cursor` means the caps cut the tree and nothing more can be resumed: re-run with looser `--max-depth` / `--max-tokens`.
- Canvas-heavy pages now expose their **canvas regions as `@eN` refs** in the observation (unplaced regions are grouped under a fallback label), rather than being invisible to semantic reading. `bsk screenshot --ref @eN` accepts those refs and captures the DOM element or Canvas region; point clicks on a canvas region are supported too. Re-take a fresh observation after any capture or navigation — canvas identity is revalidated before a click, and stale visual refs are rejected.

## Full-page screenshots (0.2.4+)

```bash
bsk screenshot --session demo --full-page --out page.png
bsk screenshot --session demo --full-page --timeout 5m --out page.png --json
```

- `--full-page` is **mutually exclusive with `--ref`**; the element crop and viewport capture paths are unchanged.
- Default capture/encoding deadline is 2 minutes; raise it with `--timeout` (`5m`, `180s`). CLI needs `--timeout` units — bare numbers mean milliseconds.
- Works on scriptable HTTP(S) pages. Restricted browser pages, nested scrollers and virtualized lists are unsupported; a failure returns an error, never a partial image.
- The CLI writes to a temp file and atomically replaces `--out` only after the full byte count validates, so a cancelled or failed capture never leaves a half-written PNG.
- The Python helper exposes this as `screenshot.py --full-page` (and `screenshot.ps1 -FullPage`); `--timeout` there is in seconds.

The daemon performs `tool.screenshot_full_page`, then bounded `tool.screenshot_read` chunks (≤ 256 KiB each) and `tool.screenshot_release`. Failure, timeout and Ctrl-C all restore the page's scroll position and temporary styles. See [long-screenshot.md](long-screenshot.md) for limits, quota behavior and the user-facing Quick Actions equivalents.

## User-scope tabs (fork build)

`--browser-id <instance-id>` operates on a connected browser's own windows instead of the Agent Window, and never creates a session. It always takes the value from `bsk browsers`, never a smart label.

```bash
bsk browsers
bsk tab list --browser-id 03c3e47f --scope user --json
bsk tab observe --browser-id 03c3e47f --tab-id 42 --expected-origin https://example.com
bsk tab select 42 --browser-id 03c3e47f --expected-origin https://example.com
bsk tab create https://example.com --browser-id 03c3e47f
```

`tab observe` is read-only: it returns the visible viewport text of that tab plus `origin`, `window_id` and a `document_id`, using a content receiver with no script injection, no CDP, and no access to form values, storage or network. Use it to confirm page identity before deciding whether a borrow is needed. See [user-tab-control.md](user-tab-control.md).

## Daemon location and startup

| Variable | Purpose |
|---|---|
| `BSK_HOME` | Overrides the daemon runtime directory (default `~/.bsk`); both sides of a shared setup must point at the same path |
| `BSK_AUTO_START` | `0` disables implicit daemon startup — commands then connect only, and report the problem if nothing is listening |

`bsk daemon start` accepts `--daemon-idle <dur>` (default 10m) and `--session-idle <dur>` (default 5m). Sandboxed shells that reap child processes need this arrangement; see [sandboxed-agents.md](sandboxed-agents.md).

## File transfer (bsk 0.2.2+)

`upload` and `download` stage files through the daemon; the agent never touches browser-internal paths. Treat upload as disclosure to the website, download as accepting website-controlled bytes.

Upload has two independent mechanisms — choose explicitly, never rely on automatic fallback:

- **Default (input mode):** for upload buttons, file-input labels, or "upload from computer" actions. The command clicks the target and intercepts the native file chooser.
- **`--mode drop`:** for reliably identified attachment-receiving areas — an explicit drop zone, chat composer, email editor, or form attachment area. Do not target page whitespace or ambiguous containers.

Decision sequence when uploading:

1. Try input mode (the default).
2. If it returns `reason=file_input_not_activated` with `effect_state=none`, re-observe. When a reliable attachment target exists, try `--mode drop` once against that target.
3. Otherwise fall back to `request-help`.
4. Never switch mechanisms or repeat when `effect_state` is `unknown` or `committed` — the browser may already have applied the file.

A successful drop means Chrome dispatched the native file-drop event; it does not prove the site accepted the attachment. Observe the page once after the command.

## Privacy constraints

- Request only the minimum snapshot, screenshot, PDF, evaluation result, or network data needed for the task.
- Never use `evaluate` to read cookies, password values, authentication tokens, browser storage, or unrelated private page state.
- Treat network headers and bodies as sensitive. Do not collect `Cookie`, `Set-Cookie`, `Authorization`, or token-bearing payloads.
- Keep large or sensitive artifacts on disk rather than returning their contents in command output.
- Remove temporary artifacts after inspection unless the user requested a retained file.

### Advanced action privacy

- Use file upload only for local files the user explicitly confirmed. Do not construct hidden upload requests.
- Treat screenshot outputs as sensitive artifacts. Delete temporary screenshots after use unless the user asked to keep them.

## Interaction rules

- Prefer fresh observation refs over CSS selectors. `bsk observe` is the default reading command; `snapshot` is the stricter static fallback.
- Snapshot refs such as `@e10` are BrowserSkill references, not DOM attributes. They work with `click` and `fill`, but selectors such as `[data-ref="@e10"]` usually do not exist.
- Refresh the observation after navigation or major DOM changes.
- `fill` validates the result before reporting success (bsk 0.2.2+). Follow the returned code instead of blindly repeating: `fill_value_mismatch` — observe the field first, the page may have formatted the value (currency, phone, date); continue if the visible result satisfies the intent. `fill_target_changed` — re-observe and retry once with a fresh ref. `target_not_fillable` — pick the real input field from a fresh observation.
- Treat `click` and `fill` as synthetic DOM events. Sites requiring `event.isTrusted` may reject them.
- Treat `fill` as clear-and-replace. Read and concatenate the existing value before filling when appending.
- Wrap repeated `evaluate` code in an IIFE to avoid top-level `const` or `let` redeclaration:

```javascript
(() => {
  const link = document.querySelector("a");
  return link?.href ?? null;
})()
```

- To recover a link when an `@e` click does not navigate, locate the DOM link by stable visible text or another real attribute and return only its URL:

```javascript
(() => {
  const link = Array.from(document.querySelectorAll("a"))
    .find((item) => item.textContent?.includes("显卡日报"));
  return link?.href ?? null;
})()
```

- Click a submit button directly when possible. Use `press` for special key events.
- Top-frame actions cannot access cross-origin iframe contents. Navigate to the iframe URL directly when appropriate.
- For long pages, use `bsk scroll-to @eN` to reveal the target and `bsk wheel --delta-y 800` to advance (0.2.4+), then take a fresh snapshot. The `evaluate` recipe below is a fallback for older builds:

```javascript
(() => {
  window.scrollBy({ top: 800, behavior: "instant" });
  return { scrollY: window.scrollY, height: document.documentElement.scrollHeight };
})()
```

## Waiting and retrying

- After `navigate` or a click that should change the page, run `wait_for.py` for the expected URL, title, or visible text; then take a fresh snapshot and inspect URL/title.
- Retry the observation up to three times with a short delay when the page is still loading.
- Do not blindly repeat the click while waiting. Repeated clicks can open duplicate tabs or submit an action twice.
- If the page remains unchanged, follow the tab and popup recovery flow below.
- `wait_for.py` polls snapshots and exits nonzero on timeout; it does not repeat the original click.

## Tab and popup behavior

- A click may open a background tab without changing the visible page.
- **If `tab list` shows no destination tab, the browser may have blocked the popup or new window. Ask the user to allow it for the site before retrying.**
- If no tab appears and the clicked element is a link, use `evaluate` to read its real `href`, then call `navigate` directly.

## Rich-text editors

`fill` is a plain-text clear-and-replace action even when the target is `contenteditable`. It does not provide bold, italic, or range-preserving rich-text semantics. Prefer accessible editor toolbar controls. If they are unavailable, report the formatting step as unsupported rather than claiming success.

## Closing sessions safely

```powershell
bsk session stop <session-id>
```

```bash
bsk session stop <session-id>
```

Before stopping the session, call `bsk tab list` and verify that every listed tab was created for the task.

## Local web app smoke-test recipe

For localhost apps where the task owns a fresh tab:

1. Run `doctor.py --wait-connected 20`; proceed only when ready.
2. Start a session with `bsk session start`.
3. Call `bsk navigate <url>` or `bsk tab create --url <url>`.
4. Take `snapshot.py --mode compact` and use `@e` refs for login, edit, or toolbar controls.
5. After every click that should open a modal or update an SPA, call `wait_for.py --text-contains ...` or take a fresh compact snapshot.
6. Use `evaluate` only for bounded state checks such as `location.href`, modal class names, title text, or console error arrays.
7. Call `bsk tab list`; if the selected tab is task-owned, close it via `bsk session stop`. For user-owned tabs, use `bsk tab return <tab-id>` instead.