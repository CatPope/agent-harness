---
name: background-task-watchdog
description: >-
  Use whenever you launch a long-running or background shell command
  (run_in_background, npm/pip install, builds, tests, downloads, npx checks,
  remote calls). Background jobs sometimes hang in an infinite loop or exit
  WITHOUT sending a completion notification, so do not wait passively on the
  notification alone — verify on a time bound and act if it stalls.
---

# Background Task Watchdog

Background/long jobs can (1) loop forever, or (2) finish but never fire the
completion notification. Relying only on the notification can leave you stuck.
Always watch them on a time bound.

## Procedure

1. **Estimate & record.** Before launching, note what "done" looks like (a
   terminal success line in the output) and a rough max expected duration
   (e.g. npm i ~1–2 min, download depends on size, a check ~30–60s).

2. **Launch, then set a checkpoint — don't wait blindly.** After starting the
   job, plan an explicit check at ~the expected duration instead of assuming
   the notification will arrive. Pick the lightest mechanism:
   - Re-read the job's **output file** (`tail`/Read) to see current progress.
   - If the harness may not wake you, use `ScheduleWakeup` (fallback tick,
     1200s+ for idle; shorter only when actively polling external state) or a
     `Monitor` until-loop to poll a concrete condition.

3. **On checkpoint, classify:**
   - **Terminal success line present** → done, proceed (verify the result, don't
     just trust exit code).
   - **Still running, output advancing** → fine, extend the checkpoint.
   - **Still running, output unchanged past max expected / spinner forever** →
     treat as **hung / infinite loop**. Inspect (last output lines, is the
     process alive?), then stop it: `TaskStop` for a tracked job, or kill the
     PID. Diagnose root cause before retrying — never relaunch into the same
     hang.
   - **Process gone but no notification fired** → read the output file to get
     the real result; continue from there.

4. **Never claim completion from a background job without reading its output.**
   A completion notification (or exit 0) is not proof — confirm the expected
   terminal line / artifact actually exists.

## Notes

- Prefer `run_in_background` for genuinely long ops, but pair it with a
  time-bound check per above.
- Avoid foreground `sleep` loops to wait; use `Monitor`/`ScheduleWakeup`.
- On Windows, watch for commands that prompt (UAC, interactive) — they can
  appear to "hang" while silently waiting for input; those must be run by the
  user or made non-interactive.
- **A process started with `&` inside a foreground shell call is not a tracked
  job.** It may keep running after the call returns, but no completion
  notification will ever come. Launch long jobs with `run_in_background`
  instead. If something is already running untracked, start a separate
  `run_in_background` watcher that loops until the job's own end marker
  appears (e.g. `until grep -q '<end line>' log; do sleep 10; done`) — that
  watcher's completion is the notification.
- When a job writes a structured log (start / pid / end lines), wait on the
  **end line for that job name**, not on process absence: the process list
  also contains unrelated helpers with similar command lines.
- When a Python job's stdout is redirected to a file that a watcher tails,
  start it with `python -u` (unbuffered). Otherwise its lines are written only
  at exit and the watcher sees nothing while it runs.
- A `tail -f` based Monitor never exits on its own. Make its filter match the
  job's final line too, and stop the monitor (TaskStop) once that line arrives.
- A `( … ) &` subshell started inside a foreground shell call can be killed
  when that call returns. Its later steps never run (seen: a test run finished
  and wrote its output, but the `ruff` step chained after it in the same
  subshell never ran and its output file was never created). Use
  `run_in_background` for multi-step background work, and check that every
  expected output file exists before trusting the result.

## History
- 2026-10-16 — A background `( pytest …; ruff … ) &` inside a foreground call
  produced the pytest output but no ruff file; the call had ended. Re-ran ruff
  directly. Added the note above.
- 2026-10-15 (afternoon) — Ran a review loop in the background with
  `python -u` output to a file and a `tail -f | grep` Monitor that emitted one
  line per finished item. The monitor kept running after the loop ended and was
  stopped by hand. Added the unbuffered-output and stop-the-monitor notes.
- 2026-10-15 — Added the untracked `&` job and end-marker watcher notes. A long
  review run was started with `&` in a foreground call; it survived, but no
  notification arrived, so an until-loop watcher on the log's end line was
  added as a background task.
