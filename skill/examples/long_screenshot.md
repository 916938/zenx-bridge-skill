# Capture a Whole Page as One Image (0.2.4+)

Use this when the task needs visual evidence of an entire page — a design review, a long report, receipt pages, or "send me what this looks like".

Requires a bsk build newer than the 0.2.3 release. Check first:

```bash
bsk screenshot --help | grep -- --full-page
```

No match means the flag is absent: fall back to the viewport-staggering recipe at the bottom.

## 1. Get the page into a stable state

```bash
SESSION_ID=$(bsk session start --name "full-page capture")   # --name labels it in operation audit
bsk navigate "https://example.com/report" --session $SESSION_ID
python3 scripts/wait_for.py --session $SESSION_ID --title-contains "Report" --timeout 15
bsk observe --session $SESSION_ID
```

Confirm anything lazy-loaded has settled. The capture waits for a stable document height at the tail, but a page that keeps appending can still consume your whole deadline.

## 2. Capture

```bash
# Python helper (writes into the temp screenshot dir, prints the resolved path)
python3 scripts/screenshot.py --session $SESSION_ID --full-page --timeout 300

# Or the CLI directly, choosing the output path
bsk screenshot --session $SESSION_ID --full-page --out ./report.png --timeout 5m --json
```

PowerShell equivalents:

```powershell
$sessionId = bsk session start --name "full-page capture"
& scripts\screenshot.ps1 -Session $sessionId -FullPage -TimeoutSec 300
```

`--timeout` is the capture/encoding deadline. The helper takes seconds; the CLI takes a duration string (`5m`, `180s` — bare numbers mean milliseconds). Default is 2 minutes.

## 3. Verify before trusting it

- Read the JSON result: check `width` / `height` and `byte_size`, and open the PNG. A successful command always wrote a complete image — there is no partial-success path.
- The page's scroll position and temporary capture styles are restored afterwards, so take a fresh `bsk observe` if you plan further interaction.

## 4. Clean up

```bash
bsk session stop $SESSION_ID
rm -f ./report.png   # temporary artifacts are sensitive
```

## When full-page capture fails

| Cause | What to do |
|---|---|
| Restricted browser page (`chrome://`, Web Store) or a nested/virtualized scroller | Not supported. Use staggered viewport captures (below). |
| `--full-page` used with `--ref` | The two are mutually exclusive — run one per purpose. |
| Timeout on an infinite feed | Either accept earlier content with popup **Finish and keep** (user-driven), or cap the page first (e.g. a "load all" control or a paginated URL) |
| CLI/extension version mismatch | Update both, then `bsk daemon restart`. Older extensions reject the new RPC instead of returning a wrong image. |

Staggered fallback — scroll, shoot, repeat:

```bash
bsk screenshot --session $SESSION_ID --out ./part-1.png
bsk wheel --delta-y 900 --session $SESSION_ID          # 0.2.4+
python3 scripts/wait_for.py --session $SESSION_ID --timeout 3 || true
bsk screenshot --session $SESSION_ID --out ./part-2.png
```

Wheel succeeds once the event is dispatched, not once scrolling finished — always wait or observe between captures.
