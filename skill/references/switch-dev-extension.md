# Switching the unpacked extension across Edge profiles

Read this when the fork's extension build moves to a new directory (repo moved/renamed) and every Edge profile still points "load unpacked" at the old path — or when an instance's extension shows the wrong version / will not connect after a rebuild.

The helper is `../../scripts/switch_extension.py` (repo root, read-only by default).

## How Chrome/Edge stores unpacked extensions

This is the part that is not obvious and easy to get wrong:

- **Unpacked ("load unpacked") extensions are NOT in `User Data\Extensions\`.** That directory only holds web-store/CRX installs. An unpacked extension exists solely as an entry in the profile's **`Secure Preferences`** under `extensions.settings.<id>.path`, holding an absolute directory.
- A web-store entry is recognisable by a *relative versioned* path (e.g. `dmaldhchmoafliphkijbfhaomcgglmgd\3.5.2_0`); an unpacked one is an absolute path ending in the build dir (e.g. `...\dist\chrome-mv3`).
- Therefore "uninstall the old, load the new" is **one path rewrite per profile** — there is no separate uninstall step for unpacked extensions, the id is derived from the directory and stays stable.

## This machine's layout (verified 2026-10-04)

- One shared Edge user-data dir: `%LOCALAPPDATA%\Microsoft\Edge\User Data`
- 20 profiles: `Default` + `Profile 1..19`; each is one zenx "instance" (`D:/916938/zenxbrowser/.zenx/accounts.json` records `launch.userDataDir` + `launch.profileDirectory`)
- Extension id: `agcgbdanbihfkcdmgegblkioiiepecln` (same in all 20)
- Old path: `D:\916938\browserskill-new\apps\extension\dist\chrome-mv3`
- New path: `D:\916938\zenx-bridge-main\apps\extension\dist\chrome-mv3`

## Procedure

1. **Build the new extension first** (in the fork checkout):
   ```powershell
   node ..\..\node_modules\.pnpm\wxt@<ver>\node_modules\wxt\bin\wxt.mjs build   # -> apps/extension/dist/chrome-mv3
   ```
2. **Dry run** — reports what would change per profile:
   ```bash
   python3 scripts/switch_extension.py
   ```
3. **Close every Edge window** (all 20 instances). This is mandatory: the browser rewrites these files on exit and would clobber the edit. The script refuses to continue while `msedge.exe` is alive.
4. **Apply**:
   ```bash
   python3 scripts/switch_extension.py --apply
   ```
5. **Start the instances again**, then confirm with `bsk status --json` — every browser should report `extension_version` matching the new build and `version_skew: false`.

Useful flags: `--profiles Default "Profile 3"` (subset), `--old-path` / `--new-path` (override), `--user-data-dir`, `--json` (machine-readable), `--no-backup`, `--force` (edit with Edge running — unsafe, only for profiles you know are not loaded).

## Safety design

- Refuses to write while Edge runs.
- Validates the new directory really contains a `manifest.json` before touching anything.
- Backs up each edited file to `Secure Preferences.zenx-bak` (skipped if a backup already exists).
- Only rewrites entries whose stored path equals the old path; profiles already switched are reported `already new` and left alone, so re-running is idempotent.
- Default is dry run; `--apply` is required for any write.

## Failure modes

| Symptom | Cause / action |
|---|---|
| "no unpacked entry" for a profile | That profile never had the extension loaded; load it manually once via `chrome://extensions`, afterwards the script manages it |
| Profile reverts to the old path | Edge was running during `--apply`, or it was launched before the edit and re-saved its own state on exit — close everything and re-apply |
| Extension id differs between profiles | Loaded from different directories at different times; pass `--old-path` per batch, or check `extensions.settings` in that profile's `Secure Preferences` |
| `version_skew: true` after switch | The daemon and extension disagree on protocol version; rebuild both and restart |
| Browser is Chrome, not Edge | Point `--user-data-dir` at `%LOCALAPPDATA%\Google\Chrome\User Data`; the process guard still checks for `msedge.exe`, so close Chrome manually and use `--force` |
