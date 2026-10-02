# AGENTS.md

## What is this

ZenX Bridge Skill is an agent skill that wraps the `bsk` CLI with Python/PowerShell helpers, examples, and layered documentation. It does not contain the CLI or extension source — those live in the [BrowserSkill repo](https://github.com/Tencent/BrowserSkill).

## Structure

| Path | What it is |
|------|------------|
| `skill/SKILL.md` | Primary agent instructions — read this first. |
| `skill/references/protocol.md` | Command parameters, exit codes, privacy constraints. |
| `skill/references/operations.md` | Installation, status checks, failure recovery. |
| `skill/references/long-screenshot.md` | Full-page capture contract and limits (bsk 0.2.4+). |
| `skill/references/wheel.md` | Native wheel input semantics (bsk 0.2.4+). |
| `skill/references/scroll-to.md` | Element reveal, visible bounds, error codes (bsk 0.2.4+). |
| `skill/references/operation-audit.md` | Local audit log scope, storage and retention (bsk 0.2.4+). |
| `skill/references/sandboxed-agents.md` | Shared daemon (`BSK_HOME` + `BSK_AUTO_START=0`) for sandboxed shells. |
| `skill/references/user-tab-control.md` | `--browser-id` user tabs, read-only `tab observe`, and `bsk browsers close` (fork build) |
| `skill/references/command-registry.json` | **Single source of truth for the command tables** in `SKILL.md` and `protocol.md`. |
| `skill/references/how-it-works.md` | Architecture and design rationale (human-only, high context cost). |
| `skill/examples/` | End-to-end workflow examples (form fill, scroll, popup, network, record + replay, long screenshot, user tabs). |
| `skill/scripts/` | Python and shell helpers (`doctor.py`, `snapshot.py`, `screenshot.py`, `wait_for.py`, `invoke.ps1`, `invoke.sh`, `record.ps1`, `record.sh`, `network.ps1`, `network.sh`, `replay.py`). |
| `skill/agents/openai.yaml` | Optional OpenAI/Codex UI metadata. |
| `tests/` | Unit tests for the Python helpers. |

## Commands

### Run tests

```bash
python -m unittest discover -s tests -v
```

### Changing a command (do this, not a direct doc edit)

The command tables in `skill/SKILL.md` and `skill/references/protocol.md` are
generated from `skill/references/command-registry.json`. Edit the registry, then:

```bash
python3 scripts/generate_command_docs.py            # rewrite the marked blocks
python3 scripts/generate_command_docs.py --check    # verify; exit 1 on drift
```

Rules:

- Each action declares `blocks` — which generated region(s) it belongs to
  (`skill-action-map`, `skill-additional`, `protocol-actions`, `protocol-additional`).
- `command` is the protocol form (no `--session`); `cli` is the CLI form used by
  SKILL.md (defaults to `command`). `protocol_purpose` overrides `purpose` in
  protocol.md (defaults to `purpose`).
- `tier` must be one of `0.2.3` / `0.2.4+` / `fork`.
- Only text between `<!-- BEGIN GENERATED: … -->` and `<!-- END GENERATED: … -->`
  is replaced. Prose outside the markers is hand-written — never let the
  generator own it.

### Lint scripts

```powershell
# PowerShell syntax check
Get-ChildItem .\skill\scripts -Filter *.ps1 | ForEach-Object {
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName, [ref]$null, [ref]$errors
    ) | Out-Null
    if ($errors.Count) { throw $errors }
}
```

```bash
# Bash syntax check
bash -n skill/scripts/invoke.sh
```

### Smoke test (requires bsk daemon)

```bash
bsk session start
SESSION_ID=$(bsk session start)
bsk tab list --session $SESSION_ID
bsk session stop $SESSION_ID
```

## Important quirks

- **Python helpers use `bsk_client.py`** — all bsk CLI calls go through this wrapper. Do not call `bsk` directly from other scripts.
- **Windows uses `py -3`** — do not assume `python3` exists on Windows.
- **UTF-8 output** — Python helpers configure UTF-8 stdout themselves. If mojibake appears, use `--mode file` and read the file instead.
- **`invoke.ps1` safety** — `close_session` requires `-Force` flag to prevent accidental tab closure.
- **`doctor.py` is read-only** — it never sends browser actions or starts the daemon.
- **Layered docs** — `SKILL.md` for agent execution, `protocol.md` for parameters, `operations.md` for recovery, capability files (`long-screenshot.md`, `wheel.md`, `scroll-to.md`, `operation-audit.md`, `sandboxed-agents.md`, `user-tab-control.md`) loaded only for that capability, `how-it-works.md` for humans only.
- **Availability tiers** — features merged after the bsk 0.2.3 tag are documented as **0.2.4+**, and `--browser-id` user-tab commands as **fork build only**. Never document a new command as generally available; name its tier and tell agents to confirm with `bsk <cmd> --help`.
- **Docs follow the upstream repo** — the CLI source lives in `../zenx-bridge`; verify command flags against `crates/bsk-cli/src/cli/*.rs` and `crates/bsk-protocol/schema/` before writing them down.
- **Deprecated overrides stay documented** — `--unattended`, `tab borrow --no-confirm` and `BSK_REQUEST_HELP=off` still parse but do nothing; keep them listed as deprecated with their replacement rather than deleting them.

## Style conventions

- Python: follow existing patterns in `skill/scripts/`. Minimal comments, clear variable names.
- PowerShell: use `[CmdletBinding()]`, named parameters, `-ErrorAction Stop`.
- Bash: `set -euo pipefail`. Quote all variables.
- Markdown: 2-space indent, LF line endings.
