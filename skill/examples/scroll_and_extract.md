# Scroll and Extract Long Content

Use this pattern for articles, long documentation pages, and pages where compact snapshots omit important static text.

1. Start with `snapshot.py --auto`.
2. If the result is compact but the task needs article/body text, rerun:

   ```powershell
   py -3 scripts\snapshot.py --session "article-task" --mode file
   ```

3. Read only the relevant sections of the saved UTF-8 JSON file. Do not paste the whole file into the conversation.
4. For lazy-loaded pages, scroll in bounded steps, wait briefly, then take a fresh file snapshot. Use the native scroll commands when installed (0.2.4+):

   ```powershell
   bsk wheel --delta-y 900 --session "article-task"
   py -3 scripts\wait_for.py --session "article-task" --text-contains "expected text" --timeout 10
   py -3 scripts\snapshot.py --session "article-task" --mode file
   ```

   For Bash:

   ```bash
   bsk wheel --delta-y 900 --session "article-task"
   python3 scripts/wait_for.py --session "article-task" --text-contains "expected text" --timeout 10
   python3 scripts/snapshot.py --session "article-task" --mode file
   ```

   Reveal one specific element with `bsk scroll-to @eN` instead when you know its ref. Wheel success only means the event was dispatched — wait or observe before the next snapshot. On older builds, substitute the bounded `evaluate` form:

   ```bash
   bsk evaluate "(() => { window.scrollBy({ top: 900, behavior: 'instant' }); return window.scrollY; })()" --session "article-task"
   ```

5. For a single image of the whole page, `bsk screenshot --full-page` does the stitching (0.2.4+) — see [long_screenshot.md](long_screenshot.md). Otherwise use `screenshot.py` at the current scroll position; the base skill deliberately adds no image-processing dependency.

