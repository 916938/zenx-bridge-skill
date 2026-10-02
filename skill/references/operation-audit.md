# Operation audit (0.2.4+)

Operation audit lets a user review, per task, what BrowserSkill did on their behalf. It is **off by default**, stored only on the machine running the daemon, and never uploaded.

Unless stated otherwise, this whole file describes features merged after the 0.2.3 release. They require matching CLI and extension builds.

## What an Agent needs to know

```bash
bsk session start --name "整理本周待办"
```

- One BrowserSkill **session = one audit task**, with its own UUID. Reusing a short session id never merges into an earlier task.
- Unnamed tasks are listed by site and start time. Prefer `--name` when the user asked for a specific job — it appears in their history.
- Statuses are 执行中 / 已结束 / 已中断 ("running / ended / interrupted"). They describe the **session**, not whether the user's goal was achieved.
- Timeouts, missing return values and mid-task recording stops are recorded as unknown outcomes. **Never infer success from silence**: if a command did not return, say so.
- Several internal operations triggered by one scripted command are recorded as a single script call; the audit log cannot reconstruct individual clicks.

## Where records live

| System | Default directory |
|---|---|
| macOS | `/Users/<user>/.bsk/audit/` |
| Windows | `C:\Users\<user>\.bsk\audit\` |
| Linux | `/home/<user>/.bsk/audit/` |

With `BSK_HOME` set the directory is `<BSK_HOME>/audit`. One task is one `<start-timestamp>-<uuid>.jsonl` file. Directory mode `0700`, files `0600` (Windows inherits user-directory permissions). Retention is 30 days for ended tasks; a ~16 MiB per-task cap applies. Uninstalling the extension does not delete these files — tell users who ask for full removal where to look.

The toggle itself is stored in the browser profile (`chrome.storage.local`), so enabling it is a user action in the popup: **rocket icon → Quick actions → 操作审计**.

## What is recorded — and what is not

Recorded metadata only: task id, timestamps, tool type, tab index, site **origin (scheme + host + port)**, cached element names, operation status, error codes, and a few counts. Navigation targets and the pre-operation page are stored separately. Inputs are recorded as "hidden".

Never recorded: screenshots, page text, DOM, **input values**, script bodies, full selectors, raw error messages, uploaded file contents, or local file paths. Element names and task names are truncated and lightly masked — still avoid putting secrets in `--name`.

Auditing is a personal-review feature, not tamper-proof evidence. Access is limited to the extension pages via the daemon; content scripts cannot call it, and each connected browser instance only sees its own tasks.

## Failure handling

Offline daemon, unsupported version and storage failures surface as explicit notices; they must never be displayed to the user as "no tasks yet". When a write fails, the not-yet-dispatched operation is skipped and the user is told to check the audit page or turn auditing off. On read-back, a trailing half-written event is discarded rather than treated as success.
