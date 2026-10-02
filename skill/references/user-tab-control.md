# User-scope tab control (fork build)

These commands operate on the user's own browser windows — not on the Agent Window and without creating a session. They come from the `916938/zenx-bridge` fork (tab commands merged 2026-09-14, `browsers close` merged 2026-09-17) and are **not** in Tencent/BrowserSkill releases. Verify with `bsk tab <subcommand> --help` / `bsk browsers close --help` before using them.

```bash
bsk browsers                                          # take instance_id from here
bsk tab list --browser-id 03c3e47f --scope user --json
bsk tab observe --browser-id 03c3e47f --tab-id 42 --expected-origin https://example.com
bsk tab select 42 --browser-id 03c3e47f --expected-origin https://example.com
bsk tab create https://example.com --browser-id 03c3e47f
```

| Command | What it does |
|---|---|
| `bsk tab list --browser-id <id> --scope user` | List that browser's user tabs (`tab_id`, `title`, `url`, `window_id`, `active`). `--scope user` is **required** with `--browser-id`; no session needed. |
| `bsk tab observe --browser-id <id> --tab-id <id> --expected-origin <url>` | Read-only capture of the tab's visible viewport text, to verify page identity before acting. |
| `bsk tab select <tab-id> --browser-id <id> [--expected-origin <url>]` | Activate a user tab and refocus its original window. Pass the origin to re-verify the tab first. |
| `bsk tab create <url> --browser-id <id>` | Open a tab in the user's own window instead of the Agent Window. URL must be absolute HTTP(S) with no credentials. |

Rules that hold for all four:

- `--browser-id` always takes the exact `instance_id` from `bsk browsers` — never a smart label. It is mutually exclusive with `--session`.
- Tab ids must be obtained from `bsk tab list`; never invent one.
- `--expected-origin` must be a bare HTTP(S) origin (`https://example.com`), with no path, query, fragment, credentials, spaces or backslashes. `tab observe` requires it and the daemon re-checks the returned origin, tab id, browser id, window id and `document_id`; a mismatch is a protocol error, not silently ignored content.

## Read-only observation

`tab observe` returns:

```json
{
  "browser_id": "03c3e47f",
  "tab_id": 42,
  "window_id": 3,
  "origin": "https://example.com",
  "document_id": "a1b2c3",
  "text": "...",
  "truncated": false
}
```

- It uses a read-only content receiver: **no script injection, no CDP, no access to form values, storage or network bodies.** Only what is visibly rendered in the viewport is returned.
- `--max-chars` bounds the response: default `4000`, maximum `8000` (with an additional ~16 KiB byte cap). Use it to keep context small; `truncated: true` means the page had more text.
- Use it to answer "am I looking at the right tab?" before deciding whether a borrow is justified. It is not a substitute for `bsk observe` inside a session, which yields controls and `@e` refs.

## Observation is not authority to act

Reading a user tab does not grant write access. When an actual interaction is required:

```bash
SESSION_ID=$(bsk session start --browser-id 03c3e47f)
bsk tab borrow 42 --session $SESSION_ID
bsk observe --session $SESSION_ID
# … act …
bsk tab return 42 --session $SESSION_ID
bsk session stop $SESSION_ID
```

Return borrowed tabs as soon as the step is done. Whether the borrow asks for confirmation is decided by the extension's **借用标签页前确认 / Confirm before borrowing tabs** setting; `bsk tab borrow --no-confirm` is deprecated and ignored. `bsk tab borrow --timeout <dur>` needs daemon protocol 1.2 and only bounds how long to wait for that confirmation.

## Closing a browser instance

`bsk browsers close` is the one command that reaches outside a session. It stops every session of that instance, closes **all** of its windows, and lets the browser process exit.

```bash
bsk browsers                                          # take instance_id from here
bsk browsers close --browser-id 03c3e47f --confirm
bsk browsers close --browser-id 03c3e47f --confirm --json   # look for "disconnected": true
```

| Flag | Purpose |
|---|---|
| `--browser-id <id>` | Exact `instance_id` from `bsk browsers`; smart labels and prefixes are rejected |
| `--confirm` | Required acknowledgement — the command refuses to run without it |

- **Not a cleanup command.** Use `bsk session stop <id>` to end your own work. This closes windows the agent never touched and discards anything unsaved in them.
- Only close an instance the user explicitly asked to close, after the work on it is done. Read `bsk browsers` first; never guess the id.
- The browser may exit mid-call, so a reply may never arrive. The daemon reports success when the instance has actually left the registry — `disconnected: true` in `--json`. A timeout means the browser is still running.
- On a 0.2.3 extension the RPC is missing and the daemon answers `unknown_method: browser.close not implemented in extension`. Treat that as "this build cannot do it" and stop the sessions manually instead.
- `bsk` never starts browsers, so there is no matching "open" command.

## Privacy

The visible text of a user tab is still page content — request only enough to confirm identity (`--max-chars` is cheap insurance) and do not run this on banking, SSO or password-manager pages just to check where you are. Ask the user instead.
