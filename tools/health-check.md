# Weekly health check (phone summary)

The health report itself is written **every day, without a model**: `tools/health.py` runs in the daily Action straight after `tools/collect.py`, and puts `health-latest.md` on the dashboard and on the `data` branch. The rules for what counts as "Needs you", "Worth a look" and "Good to know" live in that script.

This file is the procedure for the **Monday scheduled task** (7:55am Melbourne, a fresh session). Its only job is to send the owner a short phone summary of that report. **Nobody is watching it run, so don't ask questions.** The owner is not a coder: plain Australian English, action items first, exact clicks.

The *monthly audit* (checking repos against `STANDARDS.md`) is separate: `tools/audit.py`.

## Rules

- **Read-only everywhere.** No commits, no pushes, no pull requests, no issues.
- Never put model names, emails, ids or keys in anything you write.

## Steps

1. Read the report: `git clone --depth 1 --branch data https://github.com/jcm-book-library/control-room /home/user/cr-data`, then `cr-data/health-latest.md`.
2. Check its age: the first line names the day. If it is more than 3 days old, or the `data` branch or the file is missing, that is the first "Do this first" item: "the daily dashboard run is failing: open control-room, Actions, Collect repo data and publish, and look at the newest red run".
3. Write the final message (below). Don't add findings of your own; the script decides what goes in the report.

## Final message (the only place the owner reads this)

Under 200 words:
1. **Do this first:** the NEEDS YOU lines as numbered steps with exact clicks and links (or "Nothing needs you").
2. **Worth a look** and **good to know**, one line each.
3. One line: "Full report on the dashboard: https://jcm-book-library.github.io/control-room/". A scheduled session can't see the owner's sessions; for those, say "refresh the session monitor" in a Control Room chat.
