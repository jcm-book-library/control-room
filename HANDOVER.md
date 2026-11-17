# Control Room: handover

Last rewritten: 17 Nov 2026. Rewrite this file at the end of each session; don't add to it.

## Where things stand
- Control Room coordinates the 20 repos in `jcm-book-library` (a **personal account, not an organisation**): `HOUSE-RULES.md` (how to work), `STANDARDS.md` (what every repo and app should have, version 1), `templates/`, the dashboard (`site/`, `tools/collect.py`, a daily Action), `supabase/owner-only.sql` (run 14 Nov) and `plans/SUPABASE.md`.
- **Weekly health check:** scheduled task `trig_019nd5opsbeYkCh9jkbNAxgC`, Mondays 7:55am Melbourne, first run **23 Nov**, a fresh session on Sonnet, push notification. Instructions: `tools/health-check.md`. The dashboard `data` branch exists. **Not yet tested end to end.**
- **Session monitor:** a private claude.ai page, refreshed **on demand**. The owner says "refresh the session monitor" and a Sonnet helper follows `tools/monitor-refresh.md` (about 70 seconds). The daily routine for it (`trig_01HSHw43xJYXgdWcbvYAbFmV`) is **disabled**: scheduled sessions have no `list_sessions` or `get_session`.
- Three private pages are pinned for the owner: the App Board (a launcher), the Session monitor, and "Claude Can and Can't" (a guide, version 2).

## Done in the last stretch
- Standards v1 merged. D1 (Roboto for new and rebuilt apps), D6 (Our Library keeps a separate sign-in) and D9 (`main` in the three repos) decided, and the owner switched the default branches.
- Weekly health check built, merged, scheduled, set to Sonnet.
- Session monitor refreshed (twice). The guide gained the start and finish prompts, "when to start a new chat", new terms and a worked example of adding a sport as a page.
- This handover, `tools/monitor-refresh.md` and a small clarification in `STANDARDS.md` (open PR).

## Decisions the owner has made (and why)
- Apps stay in separate repos. One login comes from Supabase, not from merging code. The "hubs" are groups in a shared left rail: Life, Money, Home, Workshop, Entertainment, Travel, Sport.
- Archive repos you give up on; don't delete. The dashboard skips archived repos.
- Lessons become standards through a `standard` issue in this repo, read by the monthly audit. The owner decides.
- New session at about 50% context. Finish prompt, then **merge its PR**, then the start prompt (`STANDARDS.md` section 4).
- The weekly check opens a pull request only when something needs attention. It can't see sessions.
- The monthly audit gives a report plus proposed fixes; fixes are small per-repo PRs after the owner's OK. Automatic PRs only for mechanical fixes, after about two months.

## Next steps (in order)
1. Optional before Monday: fire the health-check trigger once and read the result. Can a scheduled session add repos and open a PR? If not, the report goes in its final message.
2. **Monthly audit:** `tools/audit.py` (no model needed) checks the STANDARDS ids marked *auto* against every repo (ignoring the three build-script settings) and compares with `reports/baseline-2026-11-16.json`. A model then proposes fixes. Move the weekly check to fortnightly after 4 weeks, then monthly.
3. **Left rail:** a small `kit` repo (rail, shared sign-in, theme) loaded by each app at a pinned version. Mock it first. It shows each person only the apps their `audience` allows (the database lock is the real security). Phones need a drawer. First across-the-board update.
4. Add `shopping-list`, `the-big-move`, `travel-app` and `travel-planner` to the App Board.

## Gotchas
- The sandbox can't reach `jcm-book-library.github.io`, so sessions read dashboard data from the `data` branch with git.
- Scheduled sessions: no connectors, no repos attached, no session tools, and they can push a phone notification themselves.
- A new session starts from `main`, so a handover only helps once its PR is merged.
- Our Library is at `ourlibrary.au` and keeps a separate sign-in (D6). Its `HANDOVER.md` is about 3,500 words and needs trimming (D7).
- Recall Arcade's handover is `docs/HANDOVER.md`, not at the top level.
- Never put the owner's email, or session titles and summaries, in this public repo.
- This checkout tracks only `main`: after pushing a new branch, add its fetch refspec or a stop hook will say it is unpushed.

## Open questions for the owner
- D2 to D5, D7 and D8 take the recommendations unless the owner says otherwise.
- Sports Tracker: once it moves to Supabase, should each competition be a row of data instead of its own Google Sheet?

## Files that matter
- `tools/health-check.md`, `tools/monitor-refresh.md`: the two on-demand and scheduled procedures.
- `tools/collect.py`, `.github/workflows/collect.yml`: the dashboard data.
- `STANDARDS.md`, `reports/baseline-2026-11-16.json`: the standard and the audit's starting facts.
- `plans/SUPABASE.md`: moving apps to Supabase and the owner-only lock.

## Start the next session with
> Repo: control-room. Task: build the monthly audit script (`tools/audit.py`) against STANDARDS.md. Size: one stage. Done when: it lists which repos are behind the standard and the baseline comparison is in the report. Read CLAUDE.md and HANDOVER.md first.
