# Full-page screenshots (0.2.4+)

`bsk screenshot --full-page` scrolls a scriptable HTTP(S) page from top to bottom and stitches one PNG. It shares its capture pipeline with the extension's **Quick actions → Full-page screenshot**, but the Agent path has stricter failure rules.

Unless stated otherwise, this whole file describes features merged after the 0.2.3 release. Check `bsk screenshot --help` before relying on them.

## Agent usage

```bash
bsk session start                                    # keep the printed session id
bsk navigate "https://example.com" --session $SESSION_ID
bsk screenshot --session $SESSION_ID --full-page --out page.png
bsk screenshot --session $SESSION_ID --full-page --timeout 5m --out page.png --json
```

Python and PowerShell helpers wrap the same call:

```bash
python3 scripts/screenshot.py --session $SESSION_ID --full-page --timeout 300
```

```powershell
py -3 scripts\screenshot.py --session $sessionId --full-page
& scripts\screenshot.ps1 -Session $sessionId -FullPage -TimeoutSec 300
```

| Flag | Meaning |
|---|---|
| `--full-page` | Enable stitched capture. Mutually exclusive with `--ref`; the viewport and element-crop paths are unchanged. |
| `--timeout` | Capture/encoding deadline. Accepts `30s`, `5m`, `180s` — bare numbers mean milliseconds. Default `2m`. Must be positive. |
| `--out` | Destination PNG. The CLI writes a temp file next to it and only replaces the target once the whole byte count validates. |
| `--tab-id` | Optional. Must be a tab the session created or borrowed. |

The helper versions take `--timeout` / `-TimeoutSec` in **seconds**.

Result fields (`--json`): `tab_id`, `width`, `height`, `format: "png"`, `path`, `byte_size`, and an optional `dialogs` array. There is no whole-image base64 in the response — image bytes arrive as bounded `tool.screenshot_read` chunks (≤ 256 KiB each) and are released with `tool.screenshot_release`.

## What "success" means here

- The whole page was captured, encoded and written to disk. **There is no partial-success result:** failures, timeouts and cancellation return an error and never hand you a half image.
- Ctrl-C cancels the capture or the transfer. A page navigation or tab switch stops the capture.
- On completion, failure, timeout or cancellation the page's scroll position and temporary capture styles are restored.
- Automatic scrolling is transient page input, so it runs through the same session queue and user-interrupt gate as clicks. Take a fresh `bsk observe` afterwards rather than assuming the captured page matches what you last saw.

## Limits and prerequisites

| Area | Behaviour |
|---|---|
| Supported pages | Scriptable HTTP(S) pages. Restricted browser pages (`chrome://`, Web Store) reject content-script injection — in the popup this offers explicit **Use manual scrolling** rather than silently switching mode; from an Agent it is an error. Nested and virtualized scroll containers are not supported. |
| Page settling | At the document tail it waits for ≥ 1.5 s of stable height and 600 ms without nearby content changes. A visible loading indicator keeps capture open; without one the quiet wait is capped at 5 s so a ticking clock cannot hold it forever. |
| Size | No 32K image-height or 48-megapixel cutoff. Infinite scrollers can still hit the `--timeout` deadline. Browser storage quota, free disk space and PNG bounds remain real constraints. |
| Versions | CLI and extension builds must match. After updating the CLI, run `bsk daemon restart`; older extensions reject the new RPC instead of returning a wrong viewport-only image. |
| Storage | Image bytes are staged in the extension's OPFS and released after a successful save, after a local failure/cancellation, on session stop, and after ten minutes of inactivity. Crashes can leave temp disk data until that sweep runs. |

## Choosing an alternative

- Need evidence of what the user sees right now, or only one component? Use the plain viewport capture or `--ref @eN` crop.
- Page is a restricted browser page, an infinite feed, or a virtualized list? Take successive viewport screenshots with `bsk wheel` / `bsk scroll-to` between them instead.
- Need to read text rather than prove layout? `bsk observe` and `snapshot.py` are cheaper and far less context-heavy.

## Quick Actions (no CLI needed)

Available from the popup even with no daemon or session:

- **Full page · Automatic** — captures from the top and follows appended content.
- **Long image · I scroll** — captures from the current position while the user scrolls; keep overlapping content between screens and choose **Finish and keep** in the popup when done.
- **Visible area** — one viewport capture.

Popup captures are independent of Agent captures: no session, no Agent deadline, and pausing lets you load more content before resuming.
