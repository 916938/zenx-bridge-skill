# Work With a User's Existing Tab (Read, Then Act)

Use this when the task concerns a page the user already has open — their logged-in dashboard, an editor with unsaved work, an internal tool behind SSO — and you must not lose their state.

The rule: **read before borrowing, borrow only to act, return immediately.**

## 1. Locate the tab

```bash
bsk browsers                                   # take the exact instance_id
bsk tab list --browser-id 03c3e47f --scope user --json   # fork build: no session needed
```

Without `--browser-id`, use a session instead:

```bash
SESSION_ID=$(bsk session start)
bsk tab list --session $SESSION_ID --scope user --json
```

Match URLs and titles **client-side** — `tab list` has no server-side URL filter. Never invent a tab id.

## 2. Confirm identity without touching the page (fork build)

```bash
bsk tab observe --browser-id 03c3e47f --tab-id 42 \
  --expected-origin https://app.example.com --max-chars 800
```

This returns the visible viewport text through a read-only receiver: no script injection, no CDP, no access to form values, storage or network bodies. If the wrong tab answers, the daemon rejects the response instead of handing you someone else's page content.

- If the text already answers the user's question, **stop here** — you never opened a session or borrowed anything.
- Do not point this at banking, SSO or password-manager pages just to check where you are. Ask instead.

## 3. Borrow only when an action is required

```bash
SESSION_ID=$(bsk session start --browser-id 03c3e47f)   # or omit --browser-id in step 1
bsk tab borrow 42 --session $SESSION_ID
bsk observe --session $SESSION_ID                       # fresh refs for the borrowed tab
```

Whether a confirmation prompt appears is controlled by the extension's 借用标签页前确认 setting — `bsk tab borrow --no-confirm` is deprecated and ignored, so do not rely on it. `bsk tab borrow --timeout 2m` only bounds how long to wait for that answer (needs daemon protocol 1.2).

## 4. Scroll and act

```bash
bsk scroll-to @e17 --session $SESSION_ID --json    # reveal an element, read its visible bounds
bsk wheel --delta-y 600 --session $SESSION_ID      # native wheel input when you need direction
bsk observe --session $SESSION_ID                  # always re-read after a mutation
bsk click @e23 --session $SESSION_ID
```

Both are browser mutations with real respect for what they promise: `scroll-to` succeeds on **partial** visibility (a clipped element still returns bounds), and `wheel` succeeding only means the event was dispatched. Neither rolls back scrolling after a timeout — observe and then decide.

For many actions you can skip borrowing entirely by opening your own tab in the user's window:

```bash
bsk tab create https://app.example.com/new --browser-id 03c3e47f
```

## 5. Return the tab and stop the session

```bash
bsk tab return 42 --session $SESSION_ID
bsk session stop $SESSION_ID
```

Return borrowed tabs as soon as the step is done — never carry one across unrelated work. Do not close a user tab unless they explicitly asked; `bsk session stop` returns borrowed tabs and closes only the session's own Agent Window tabs. If the tab must stay put for the user to inspect it, you can also just select it:

```bash
bsk tab select 42 --browser-id 03c3e47f --expected-origin https://app.example.com
```
