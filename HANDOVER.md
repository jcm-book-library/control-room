# Control Room: handover

Last rewritten: 16 Nov 2026. Rewrite this file at the end of each session; don't add to it.

## Where things stand
- Control Room is the coordination repo for the 20 repos in `jcm-book-library`: `HOUSE-RULES.md` (how to work), `STANDARDS.md` (what every repo and app should have, version 1, in PR #6), `templates/`, the dashboard (`site/` plus `tools/collect.py`, rebuilt daily by a GitHub Action), `supabase/owner-only.sql` and `plans/SUPABASE.md`.
- `jcm-book-library` is a **personal account, not an organisation**. The collector uses the user-account endpoints.
- No scheduled tasks exist yet. The weekly health check and monthly audit are agreed in principle but not created.

## Done in the last stretch
- Owner-only lock for Supabase (PR #5, merged, run in Supabase on 14 Nov, The Brain still works). 94 tests in `tests/sql/owner-only.sh`.
- STANDARDS.md v1, templates and house-rules section 8 (PR #6), with a baseline of all 20 repos in `reports/baseline-2026-11-16.json`.

## Decisions the owner has made (and why)
- Apps stay in separate repos. One login comes from Supabase, not from merging code. The "hubs" are groups in a shared left rail: Life, Money, Home, Workshop, Entertainment, Travel, Sport. Big merged codebases would fill sessions faster.
- Archive repos you give up on (Settings, Danger Zone); don't delete. The dashboard skips archived repos.
- Lessons become standards through a `standard` issue in this repo, read by the monthly audit. The owner decides.
- Sessions: start a new one at about 50% context. Start and finish prompts are in `STANDARDS.md` section 4.
- Weekly check is report-only. The monthly audit gives a report plus proposed fixes. Fixes are small PRs, one per repo, after the owner's OK. Automatic PRs only for mechanical fixes, after about two months.

## Next steps (in order)
1. Owner reads and merges PR #6. D1 (Roboto for all new and rebuilt apps), D6 (separate sign-in for Our Library) and D9 (`main` in three repos) are decided; D2 to D5, D7 and D8 take the recommendations unless the owner says otherwise.
2. **D9:** `main` was created from the session branch in `travel-app` and `travel-planner` on 16 Nov 2026 (`shopping-list` already had one, with two newer commits still on its session branch). The owner still switches each of the three repos' default branch to `main` in GitHub settings, and turns on Pages from `main` where an app is live.
3. **Weekly health check:** Mondays 7:55am Melbourne (cron is UTC), a fresh session on a cheaper model, writes `reports/health-latest.md` through a PR into this repo, notifies the owner only if something needs them. Fortnightly after 4 weeks, then monthly.
4. **Monthly audit:** a script (`tools/audit.py`, no model needed) checks STANDARDS ids marked *auto* against every repo, ignoring the three build-script settings, and compares with the baseline. A model then reads the report and proposes fixes. On the first run, find out whether a scheduled session can write to the other repos. If not, it stays report-only and a manual session applies fixes.
5. **Left rail:** a small `kit` repo (rail, shared sign-in, theme), loaded by each app at a pinned version. Mock it as a picture first. It shows each person only the apps their `audience` allows, but the database lock is the real security. Phones need a drawer or bottom bar. It is the first across-the-board update; the audit then reports who is behind.
6. Add `shopping-list`, `the-big-move`, `travel-app` and `travel-planner` to the owner's App Board (a private claude.ai page).

## Gotchas
- Our Library is at `ourlibrary.au`. Sign-in storage is per address, so it cannot share a session with the apps on `jcm-book-library.github.io`. The owner accepted a separate sign-in (D6); the rail links out to it.
- Our Library's `HANDOVER.md` is about 3,500 words and holds reference material. Trim it (D7).
- A session can only change repos it was started with. Adding repos mid-session was refused once; adding `control-room` worked when asked directly.
- The earlier "repo creation failed" was a wrong call: this is a user account, so a session can probably create repos without the organisation option. Untested.
- Never put the owner's email in this public repo. `owner-only.sql` has a placeholder; the filled copy is given in chat.
- `tests/sql/owner-only.sh` needs the Books and Brain SQL as sibling checkouts or via `BOOKS_SQL` and `BRAIN_SQL`.

## Open questions for the owner
- D1 to D9 in `STANDARDS.md` section 7.
- Yes or no to creating the weekly health check, once PR #6 is merged.
- Whether the owner has switched the three default branches and where `shopping-list` is live (its session branch is ahead of `main`).

## Files that matter
- `STANDARDS.md`: the standard, session prompts, baseline, decisions.
- `reports/baseline-2026-11-16.json`: the audit's starting facts for all 20 repos.
- `plans/SUPABASE.md`: moving apps to Supabase, and the owner-only lock (section 8).
- `tools/collect.py` and `.github/workflows/collect.yml`: the dashboard data.

## Start the next session with
> Repo: control-room. Task: set up the weekly health check and the monthly audit script against STANDARDS.md. Size: one stage. Done when: the weekly task is scheduled, the audit script lists which repos are behind, and I've seen the first report. Read CLAUDE.md and HANDOVER.md first.
