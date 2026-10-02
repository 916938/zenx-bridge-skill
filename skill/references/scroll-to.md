# Scroll-to primitive (`bsk scroll-to`, 0.2.4+)

`bsk scroll-to` brings an existing element and its containing frames into view, then reports the visible part's bounds. Use it to reveal a target before inspecting the page, taking a screenshot, or interacting. Use [`wheel`](wheel.md) when you need native directional wheel input instead.

```bash
bsk scroll-to @e3 --session $SESSION_ID --tab-id 42 --timeout 5s --json
bsk scroll-to --selector '#details' --session $SESSION_ID
```

| Flag | Meaning |
|---|---|
| positional target / `--ref` / `--selector` | **Exactly one** ref (`@e3`, `e3`) or CSS selector |
| `--session` | Required |
| `--tab-id` | Defaults to the Agent Window's active tab; user tabs must be borrowed into that window |
| `--timeout` | Default `30s`, must be positive (`5000ms` and `5s` both parse) |

## Result semantics

```json
{
  "tab_id": 42,
  "used_ref": "e3",
  "x": 10,
  "y": 20,
  "width": 100,
  "height": 80
}
```

- `x`/`y` are the upper-left corner and `width`/`height` the size of the **visible** border-box rectangle, in top-level viewport CSS pixels after scrolling and clipping — not document or screenshot pixels.
- **Partial visibility is success.** A 400px-tall element clipped by an 80px-tall scroll container returns `height: 80`. Hidden or fully clipped targets fail.
- The rectangle is **not** an occlusion or hit test: another element may cover it, and its centre is not guaranteed to be clickable. Take a fresh `bsk observe` before interacting.
- The optional `dialogs` array reports JavaScript dialogs handled during the call.

## Errors

| Code | `data.reason` | Meaning |
|---|---|---|
| `invalid_params` | — | Missing or conflicting target, invalid timeout or tab id |
| `not_found` | `ref_not_found` | Ref unknown, expired, or belongs to another tab |
| `not_found` | `selector_not_found` | Main-document selector matched nothing |
| `permission_denied` | `agent_window_scope` | Tab was not borrowed into the Agent Window |
| `permission_denied` | `element_not_visible` | No visible area remains after scrolling |
| `cancelled` | — | The call was cancelled |
| `timeout` | — | The action deadline expired |
| `cdp_failed` | varies | Browser command, frame geometry or visibility measurement failed |

CSS selectors search only the main document — use refs for iframes (including out-of-process ones) and shadow roots. scroll-to is a browser mutation and therefore goes through the per-session queue and user-interrupt gate; performed scrolling is never rolled back, so inspect the current page before retrying after a cancellation.
