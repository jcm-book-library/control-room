# Control Room: handover

Last rewritten: 17 Nov 2026. Rewrite this file at the end of each session; don't add to it.

## Where things stand
- Control Room coordinates the 20 repos in `jcm-book-library`: `HOUSE-RULES.md` (how to work), `STANDARDS.md` (what every repo and app should have, version 1, merged 17 Nov), `templates/`, the dashboard (`site/`, `tools/collect.py`, a daily Action), `supabase/owner-only.sql` (run 14 Nov) and `plans/SUPABASE.md`.
- `jcm-book-library` is a **personal account, not an organisation**.
- **Weekly health check:** scheduled task `trig_019nd5opsbeYkCh9jkbNAxgC`, Mondays 7:55am Melbourne (first run 23 Nov), a fresh session each time, push notification to the owner. Its instructions are in `tools/health-check.md` (in the open pull request). **Not tested yet.**

## Done in the last stretch
- Standards v1 merged. D1 (Roboto for all new and rebuilt apps), D6 (Our Library keeps a separate sign-in) and D9 (`main` in the three repos) are decided, and the owner switched the three default branches.
- Weekly health check built: pull request dates in the collector, a daily copy of the dashboard data on a `data` branch, and `tools/health-check.md`.

## Decisions the owner has made (and why)
- Apps stay in separate repos. One login comes from Supabase, not from merging code. The "hubs" are groups in a shared left rail: Life, Money, Home, Workshop, Entertainment, Travel, Sport.
- Archive repos you give up on; don't delete them. The dashboard skips archived repos.
- Lessons become standards through a `standard` issue in this repo, read by the monthly audit.
- New session at about 50% context. Start and finish prompts are in `STANDARDS.md` section 4.
- The weekly check opens a pull request only when something needs attention. The part about the owner's sessions is private and goes in the final message only, never in the public repo.
- The monthly audit gives a report plus proposed fixes; fixes are small per-repo PRs after the owner's OK. Automatic PRs only for mechanical fixes, after about two months.

## Next steps (in order)
1. Owner merges the health-check PR, then runs the workflow once (Actions, Collect repo data and publish, Run workflow) so the `data` branch exists. Then fire the trigger once as a test.
2. Read the test run. Can a scheduled session add repos, read sessions and open a PR? Fix what it can't. If push or the GitHub tools aren't available, the report goes in the final message instead.
3. **Monthly audit:** `tools/audit.py` (no model needed) checks the STANDARDS ids marked *auto* against every repo (ignoring the three build-script settings) and compares with the baseline. A model then proposes fixes. Move the weekly check to fortnightly after 4 weeks, then monthly.
4. **Left rail:** a small `kit` repo (rail, shared sign-in, theme) loaded by each app at a pinned version. Mock it first. Audience-aware (the database lock is the real security). Phones need a drawer. First across-the-board update.
5. Add `shopping-list`, `the-big-move`, `travel-app` and `travel-planner` to the owner's App Board (a private claude.ai page).

## Gotchas
- The sandbox can't reach `jcm-book-library.github.io`, so sessions read dashboard data from the `data` branch with git.
- Scheduled tasks store no connectors and start with no repos attached.
- Our Library is at `ourlibrary.au` and keeps a separate sign-in (D6). Its `HANDOVER.md` is about 3,500 words and needs trimming (D7).
- Never put the owner's email in this public repo.

## Open questions for the owner
- Keep "PR only when something needs attention", or one every week?
- D2 to D5, D7 and D8 take the recommendations unless the owner says otherwise.

## Files that matter
- `tools/health-check.md`, `tools/collect.py`, `.github/workflows/collect.yml`: the weekly check and its data.
- `STANDARDS.md`, `reports/baseline-2026-11-16.json`: the standard and the audit's starting facts.
- `plans/SUPABASE.md`: moving apps to Supabase and the owner-only lock.

## Start the next session with
> Repo: control-room. Task: build the monthly audit script (`tools/audit.py`) against STANDARDS.md. Size: one stage. Done when: it lists which repos are behind the standard and the baseline comparison is in the report. Read CLAUDE.md and HANDOVER.md first.
