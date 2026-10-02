# BrowserSkill in a sandboxed Agent

Some Agent environments terminate a command's child processes when the command returns — including detached daemons. This reaps the bsk daemon immediately, so every later command looks like a cold start (or hangs waiting for one). The fix is to keep the daemon in the **owning host environment** and have sandboxed commands connect to it over shared local IPC.

Ordinary local use needs none of this: the daemon auto-starts and exits after its default 10-minute idle timeout.

## 1. Pick one shared directory

Choose a persistent directory owned by the user that runs the daemon; both sides must see the **same** directory at the same absolute path (`daemon.json`, `run/daemon.sock` on Unix). Matching environment-variable text is not enough if the mounts differ. Keep it private to that user rather than world-writable.

## 2. Start the daemon outside the sandbox

Run this from a normal host terminal, not from a sandboxed Agent command:

```bash
BSK_HOME=/absolute/shared/bsk bsk daemon start
```

If the Agent host offers persistent background tasks, let one own a foreground daemon instead — using the host's sanctioned mechanism, so it runs outside the sandbox:

```bash
BSK_HOME=/absolute/shared/bsk bsk daemon start --foreground
```

Do not disable sandboxing wholesale for browser commands. Start and stop this daemon only from the owning environment. Task cleanup stays `bsk session stop`, which leaves other sessions and the daemon running.

If the workflow needs a longer idle window than the default 10 minutes, pass `--daemon-idle 2h` when starting it. After an idle exit, restart it from the host.

## 3. Connect from every sandboxed command

```bash
BSK_HOME=/absolute/shared/bsk BSK_AUTO_START=0 bsk doctor
BSK_HOME=/absolute/shared/bsk BSK_AUTO_START=0 bsk session start
BSK_HOME=/absolute/shared/bsk BSK_AUTO_START=0 bsk navigate https://example.com --session SESSION_ID
BSK_HOME=/absolute/shared/bsk BSK_AUTO_START=0 bsk snapshot --session SESSION_ID
BSK_HOME=/absolute/shared/bsk BSK_AUTO_START=0 bsk session stop SESSION_ID
```

Set both variables on **every** invocation — a previous `export` usually does not carry into the next shell tool call. Retain the session id between calls.

`BSK_AUTO_START=0` disables *implicit* startup only: it still connects to a running daemon and reports the problem if none is listening, without spawning a replacement or touching runtime files. Only the exact value `0` opts out. Explicit `bsk daemon start|stop|restart` and `bsk update` are unaffected.

Use `BSK_HOME` explicitly rather than guessing usernames or rewriting a process's global `HOME`.

## Diagnostics

| Symptom | Action |
|---|---|
| Automatic startup disabled | Start the daemon from its owning host environment with the same `BSK_HOME`, then retry. Do not start a daemon inside a sandbox that will reap it. |
| Directory or permission error | Fix `BSK_HOME` and the host's access rules for that directory and its IPC endpoint. There is no fallback to a guessed user directory. |
| IPC reachable but process identity unverified | Browser commands can continue; PID-namespace differences may block signal-based management. Run lifecycle commands in the owning environment. Doctor does not fail on this alone. |
| IPC timeout or invalid reply | Inspect the daemon from its owning environment. These errors do not trigger another auto-start, and runtime files should be kept. |

Do not work around a refused stop by disabling PID identity checks or deleting lock files.

## Verify the host integration

1. Start the daemon outside the sandbox; confirm `bsk status` works inside it with the two variables.
2. Create a session, let that invocation end, then navigate and snapshot in another invocation using the same session id.
3. Stop only that session; another status call must still reach the daemon.
4. With no other active sessions, stop the daemon from the host. The next sandboxed command must report it unavailable without starting a new one — then restart it from the host.

Passing local CLI tests does not prove a particular Agent host keeps background tasks alive; only this sequence does.
