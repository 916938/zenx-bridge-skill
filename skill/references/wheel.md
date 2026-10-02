# Native wheel input (`bsk wheel`, 0.2.4+)

`bsk wheel` dispatches a real Chromium mouse-wheel event. Use it for directional scrolling and for controls that only respond to wheel input. Use [`scroll-to`](scroll-to.md) when the goal is to bring an existing element into view.

```bash
bsk wheel --delta-y 600 --session $SESSION_ID
bsk wheel --delta-y -120 --session $SESSION_ID
bsk wheel '#panel' --delta-x -200 --session $SESSION_ID --tab-id 42 --timeout 5s --json
bsk wheel @e3 --delta-y 120 --modifiers ctrl,shift --session $SESSION_ID
```

| Flag | Meaning |
|---|---|
| positional target | Optional ref (`@e3`, `e3`) or CSS selector used as the hit-test point |
| `--ref` / `--selector` | Explicit target alternatives; supply **at most one** target, and never an empty one |
| `--delta-x` / `--delta-y` | Horizontal / vertical input in CSS pixels. Both default to `0`, at least one must be nonzero, values must be finite. Positive X is right, positive Y is down. `--delta-y=-120` also works. |
| `--modifiers` | Comma-separated `alt,ctrl,meta,shift` |
| `--session` | Required |
| `--tab-id` | Defaults to the Agent Window's active tab. User tabs must be borrowed first. |
| `--timeout` | Default `30s`, must be positive |

## Result semantics

```json
{
  "tab_id": 42,
  "used_selector": "#panel",
  "x": 320,
  "y": 240,
  "delta_x": -200,
  "delta_y": 0
}
```

- Without a target the mouse moves to the viewport centre first — whatever scroller is under that point receives the input, which may be an inner container rather than the document.
- With a target, the tool scrolls the element and its frame owners into view, accounts for ancestor clipping and iframe projection, then dispatches at a visible point.
- `x`/`y` are the dispatch point in top-level viewport CSS pixels. `delta_x/delta_y` echo what you requested, not a measured displacement.
- Deltas go unchanged to CDP, whose units are CSS pixels. Page zoom changes what lands: Chromium at 125% zoom turns a 120-unit input into a 96-unit DOM delta. A page may also `preventDefault` and use the event itself.
- **Success means dispatch completed** — not that scrolling, animations or app work finished. Always take a fresh `bsk observe` afterwards.
- Moving the pointer can trigger hover UI and change the page.

## Errors

| Code | Cause |
|---|---|
| `invalid_params` | Bad input: no target with empty string, conflicting targets, both deltas zero, non-finite delta, bad timeout or modifiers |
| `not_found` | Ref unknown/expired/owned by another tab, or selector matched nothing |
| `permission_denied` | Tab not in the session's Agent Window, or target has no visible area |
| `cdp_failed` | Geometry, visibility or input dispatch failed |

Wheel is a browser mutation: it uses the per-session queue and the user-interrupt gate. On timeout the daemon cancels and waits up to two seconds for cleanup. **Already-dispatched input cannot be recalled** — inspect the page before retrying an interrupted call. Refs only search the main document when given as CSS selectors; use refs for iframe and shadow-root elements.
