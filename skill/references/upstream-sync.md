# Upstream sync: ZenX Bridge ↔ Tencent/BrowserSkill

Read this file when asked to sync the fork with upstream, to review why something was skipped, or to decide whether an upstream feature line should be adopted wholesale. The companion **record** lives in `../zenx-bridge-main/docs/UPSTREAM_SYNC.md`: that file is the per-batch ledger (ported/skipped hashes, verification numbers); **this file is the reusable procedure**. Keep both current — ledger after every batch, procedure whenever a batch yields a generalizable lesson. Repo-to-repo update rules are in `../../AGENTS.md` → Companion repositories.

Scope note: this reference is for fork maintenance, not for driving a browser. Return to `SKILL.md` for normal bsk work.

---

## 1. Position and invariants

The fork is a **downstream distribution (soft fork)**: it keeps `Tencent/BrowserSkill` as a remote and continuously absorbs upstream fixes, while identity, version line and support surface are ours. Three standing decisions:

| # | Decision | Consequence when syncing |
|---|---|---|
| 1 | Protocol layer stays compatible with upstream | Never change handshake/protocol-version semantics; this is what keeps cherry-picks cheap |
| 2 | remote / server mode is out of scope | Anything under the paths in §5 is frozen — do not port, do not extend, do not document it as a capability |
| 3 | Keep absorbing upstream fixes | Only reconsider cutting off upstream if it breaks protocol compatibility or forces server mode by default |

Additional non-negotiable rules:

- **Loopback only.** Upstream's standalone server (public listener + device pairing + TLS) violates this invariant.
- **Version line**: our version is always strictly greater than the last synced upstream version (upstream 0.3.x → us 0.4.x). Never use `+build.metadata` — semver ignores it and the release regex rejects it. Version bumps are their own release action, never a side effect of a sync batch.
- **Ours wins** in conflicts over: version numbers in manifests/lockfiles, `README*`, `CHANGELOG`, `AGENT_INSTALL*`, install URLs (`916938/zenx-bridge`), brand copy.

---

## 2. Before touching anything: agree the scope

The amount of work between "20 safe commits" and "merge everything" is an order of magnitude. **Ask before starting.** Offer exactly these three scopes:

| Scope | What it means | Pick it when |
|---|---|---|
| Portable single-commit set | Every bugfix/doc/CI fix that does not depend on an unported feature line (~35–60 commits per quarter) | Default. This is what batches so far have used |
| Conservative subset | Only zero-overlap, zero-conflict commits | Upstream drifted enormously and you need value now with minimal risk |
| Full-tree merge | `git merge Tencent/main`, manually adjudicate the conflict file list | Only if the tree has converged or a feature line must land whole |

Then land on **a dedicated branch** (`upstream-sync/<date>`), verify there, and let the owner decide about merging to `main`. Do not cherry-pick straight onto `main`.

Quantify first so the question is answerable:

```bash
git fetch Tencent
BASE=$(git merge-base HEAD Tencent/main)     # last sync baseline
git log --oneline $BASE..Tencent/main | wc -l          # total commits
git log --no-merges --oneline $BASE..Tencent/main | wc -l
git merge-tree --write-tree --name-only HEAD Tencent/main   # dry-run conflicts, touches nothing
git cherry -v HEAD Tencent/main              # "-" = already ported by us
```

`scripts/upstream_sync.py triage` (see §8) automates this into a per-commit classification.

---

## 3. Five-step procedure

1. **Fetch.** If HTTPS to github.com times out (~21 s), switch the remote to SSH — `ssh -T git@github.com` is the connectivity test:
   ```bash
   git remote set-url Tencent git@github.com:Tencent/BrowserSkill.git
   git fetch Tencent --prune
   ```
2. **List candidates and drop what we already have.** `git cherry` marks patches already applied under a different hash. Expect a dozen per quarter.
3. **Triage each commit on three axes**: (a) does it touch frozen remote paths, (b) does it depend on a feature line we did not carry, (c) how much does it overlap files we changed.
4. **Establish true ordering** — see §4; `git log` date order is not topological order.
5. **Cherry-pick in dependency order**, resolving conflicts per file with the rules in §5, then verify (§7), then record (§9).

Batching matters: apply one coherent chain (e.g. "download lifecycle") together rather than interleaving unrelated areas, so a conflict means "decide once" instead of "re-derive context".

---

## 4. The ordering trap (cost us a broken pick once)

`git log` sorts by **commit date**, not topology. Cherry-picking by date silently reverted an earlier refactor because a later-dated commit was its ancestor.

Before picking a set, confirm the real chain:

```bash
git merge-base --is-ancestor A B && echo "A before B"
```

```bash
python3 scripts/upstream_sync.py order A B C ...
```

Exception worth remembering: when a chain has already merged upstream with *another* line, sometimes the pragmatic fix is to take the **final upstream version of the touched files** instead of the individual commit, then re-apply our branding — this is how `03f8561` was landed as `5a1d816` + `f5ce66f`.

---

## 5. Conflict adjudication rules

| Conflict kind | Resolution |
|---|---|
| Version numbers in `Cargo.toml` / `Cargo.lock` / `package.json` | Keep ours |
| `README*.md`, `AGENT_INSTALL.md`, install URLs, brand strings | Keep ours, adopt only clearly additive pieces (e.g. a new PATH hint) |
| New upstream tests for the ported behaviour | Keep upstream's; drop tests that reference unported helpers |
| `skill/SKILL.md` (and its `crates/bsk-cli/skill/` copy rebuilt by `build.rs`) | Take ours structurally, merge intent by hand |
| Commonly contested files | `apps/extension/src/entrypoints/background.ts`, `popup/App.tsx`, `session-manager/manager.ts`, `tools/dispatcher.ts`, `browser-driver/chromium-cdp.ts`, `lib/connection-controller.ts`, `crates/bsk-cli/src/daemon/ws.rs`, `crates/bsk-protocol/src/method.rs`, `packages/i18n/src/locales/*/extension.json` |
| New third-party dependency in the extension | Add to `apps/extension/package.json` **and** commit the regenerated lockfile; never hand-edit `pnpm-lock.yaml` |
| CI workflows | Usually "keep both": take upstream's new job/step, but strip paths that reference things we don't carry (upstream package names, scripts that don't exist here) |

**The important failure mode**: taking "ours" in a shared core file can leave out the API the rest of the picked commit needs. Example from the 2026-10-02 batch — `b967b27` (download dispatch fence) needs `CdpDispatchGuard` / `sendGuarded` / a `beforeDispatch` hook in `chromium-cdp.ts`; keeping our version silently dropped them and only surfaced later as a compile error. When this happens, add a **separate adaptation commit** carrying the needed API without dragging in its upstream dependencies, and note it in the batch record.

---

## 6. Known unportable feature lines (do not cherry-pick in isolation)

Upstream ships most of its fixes on top of feature lines we never adopted. Picking the fix alone either fails to compile or leaves dead code.

| Feature line | Upstream entry | Blocks these recurring fixes | How to adopt if ever needed |
|---|---|---|---|
| Recoverable session starts | `8e357f3` (`session-starts.ts`, `start-journal.ts`) | `abf0d3a`, `ca02b26`, `a6c3498`, `bedcf90` | Absorb the whole line, not the dependent fixes |
| Task UI / rename / popup attribution | `9cde489`, `a15e857`, `05db608` | `80dd02a`, `7b74596`, `7478e08`, `64245fb`, `345d703`, `69dfd06`, `2aca02a` | Whole line; its dead-code residue is worse than the missing fix |
| Windows self-update / handover | chain starting `fc7561b` (`update/state.rs`, `daemon/start/handover.rs`) | 9 commits touching `cli/update.rs` | **Standalone project**: our `update.rs` diverges heavily (own release source); high release-path risk |
| dsh SDK migration | `b8b744a` chain (`0.1.0-rc.6` → `0.1.5-rc.3`) | most `fix(dsh*)` commits, incl. the known-failing plugin tests | Standalone project; see §7 baseline failures |
| Skill reference bundles / i18n packs | `45a3bf1`, `f360a34` | `47f5765`, `240bf1d`, `02e802f`, multi-locale i18n commits | Whole structural change |
| Website-debug forensics | `a3f8200` + ~16 `feat(debug)` commits | all `fix(debug)` commits | New subsystem absent from our tree: it is a feature decision, not a sync item |
| daemon startup hint module | `507522f`, `72986b2` (`daemon/start_error.rs`) | later hint-related fixes | Ours is inline in `cli/ensure_daemon.rs` / `cli/doctor.rs` |

Frozen per invariant #2 (never port at all): `crates/bsk-cli/src/daemon/remote/**`, `apps/extension/src/transport/remote-*.ts`, `docs/remote-extension-connection.md`, `crates/bsk-cli/tests/remote_server.rs`.

Never "sync" these either: pure release commits, README rewrites, privacy-policy wording.

**Lesson:** before starting a batch, decide *per feature line* whether to absorb it wholesale. Fix-by-fix picking has a low hit rate when most fixes ride on those lines.

---

## 7. Verification matrix

Run from the `zenx-bridge-main` checkout:

| Check | Command | Expected |
|---|---|---|
| Rust build | `cargo check -p bsk --locked` | Clean |
| Rust tests | `cargo test --workspace --locked --no-fail-fast` | Only the failures listed below |
| Windows lifecycle | `powershell -File scripts/test-windows-daemon.ps1` | Green (startup + launcher + update suites) |
| Extension types | `pnpm --filter @browser-skill/extension exec wxt prepare` | Generates `.wxt/` |
| Extension compile | `pnpm --filter @browser-skill/extension compile` | Clean `tsc --noEmit` |
| Extension tests | `pnpm ext:test` | All green |
| Lint/format | `pnpm lint` (biome + stylelint) | Clean |

Accepted pre-existing failures (do not "fix" during a sync):

- `cargo test -p bsk --test remote_server`: Windows file-contention semantics; the whole file is frozen territory.
- dsh plugin tests (`skill.test.ts`, `lazy-tools.test.ts`): baseline failures, unfixable without the SDK migration line.

Environment traps that masquerade as regressions:

- `windows_daemon_start` / `windows_update` fail with `Access is denied (os error 5)` when the host process sits in a restrictive Job (IDE shells). Not a code problem — re-run through `scripts/test-windows-daemon.ps1`.
- `long-screenshot/png.test.ts` 120k-scanline case can fail with `STACK_TRACE_ERROR` under full parallel load; it passes when re-run alone.
- If extension suites fail with "Failed to resolve import", the cause is almost always a broken `node_modules` link, not the sync. See §9.

---

## 8. Helper script

`../../scripts/upstream_sync.py` (repo root) automates the mechanical parts. It never writes to the repository — it only reads git state and prints tables.

```bash
python3 scripts/upstream_sync.py triage              # per-commit classification of pending upstream work
python3 scripts/upstream_sync.py triage --markdown   # same, as a triage table you can paste into a plan
python3 scripts/upstream_sync.py applied             # upstream commits we already cherry-picked
python3 scripts/upstream_sync.py order HASH...       # verify topological order before picking
python3 scripts/upstream_sync.py table               # upstream→ours mapping for the sync doc
python3 scripts/upstream_sync.py table --since 2026-10-01
```

It assumes the upstream remote is named `Tencent` and that the fork's mainline branch is `main`. Override with `--remote` / `--base`.

One caveat: `triage` uses patch-ids, so a commit we ported **with hand edits** (dropped hunks, adapted conflicts) shows up as pending again. Cross-check by subject against the ported list in `UPSTREAM_SYNC.md` §5 before re-picking.

---

## 9. Environment gotchas worth remembering

**Do not run `pnpm install` inside the IDE/agent shell.** Its safe-delete shim intercepts `unlink` during pnpm's store setup (`ERR_PNPM_LINKING_FAILED [safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]`), and it will leave workspace packages with emptied `node_modules` link directories that pnpm cannot then rebuild. `--virtual-store-dir` does not help (`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`). Ask the owner to run the install in a normal terminal.

Recovery when links are already gone (the `.pnpm` store usually survives intact):

1. Map each dependency to `node_modules/.pnpm/<escaped-name>@<version>/node_modules/<name>` using the `importers` section of `pnpm-lock.yaml` (`@scope/pkg` → `@scope+pkg`).
2. Recreate links with junctions: `New-Item -ItemType Junction -Path <pkg>/node_modules/<dep> -Target <store path>`.
3. Don't forget **peer** dependencies (e.g. `react` for `packages/ui`) and scoped workspace packages (`@browser-skill/*` → local `packages/*`).
4. `.bin` shims usually don't come back; call tools directly:
   ```powershell
   node ..\..\node_modules\.pnpm\wxt@<ver>\node_modules\wxt\bin\wxt.mjs prepare
   node ..\..\node_modules\.pnpm\typescript@<ver>\node_modules\typescript\bin\tsc --noEmit
   node ..\..\node_modules\.pnpm\vitest@<ver>\node_modules\vitest\vitest.mjs run
   node node_modules\.pnpm\@biomejs+biome@<ver>\node_modules\@biomejs\biome\bin\biome check <path>
   ```

**GitHub over HTTPS can be unreachable** (curl 28 (~21 s) timeout) while SSH works. Test with `ssh -T git@github.com`, then repoint the remote (§3). `--prune` at fetch time also surfaces upstream branches worth a look (`release/*`, `fix/*`).

**Long test runs get killed by the shell timeout.** Start them detached and poll a result file:

```powershell
node <vitest.mjs> run --reporter=json --outputFile=<temp>\vitest.json   # via Start-Process -WindowStyle Hidden
```

---

## 10. Record and iterate

After every batch, update `../zenx-bridge-main/docs/UPSTREAM_SYNC.md`:

1. Append a dated subsection under **§5 Ported**: `upstream-hash → our-hash` pairs plus the resolution note for every hand-adjudicated conflict. Generate the raw rows with `scripts/upstream_sync.py table`.
2. Append a **skipped** table with a reversible reason each time ("depends on line X; re-evaluate if we adopt X").
3. Update **§6 Known failures** with that round's verification numbers and any *new* failure pattern.

Then feed improvements back into **this file**: a new failure mode, a newly discovered unportable line, or a better recovery trick belongs here, so the next run starts smarter instead of rediscovering it. Specifically, add to this file when:

- a cherry-pick failed for a reason not yet listed in §5/§6;
- an upstream feature line first appears (add its entry point commit to §6 so later fixes can be attributed to it);
- a verification command changed (CI script renamed, new tier added);
- some local interference masqueraded as a regression and cost more than five minutes to diagnose (add it to §7's trap list).
