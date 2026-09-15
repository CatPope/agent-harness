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
