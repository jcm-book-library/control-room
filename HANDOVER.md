# Control Room: handover

Last rewritten: 25 Nov 2026. Rewrite this file at the end of each session; don't add to it.

## Where things stand
- Control Room coordinates the 20 repos in `jcm-book-library` (a **personal account, not an organisation**): `HOUSE-RULES.md`, `STANDARDS.md` (version 1), `templates/`, the dashboard (`site/`, `tools/collect.py`, a daily Action), `supabase/owner-only.sql` and `plans/SUPABASE.md`.
- **Daily health report (no model):** `tools/health.py` runs in the daily Action after `collect.py`, writes `health-latest.md` to the dashboard and the `data` branch. Replaced the session-written report, because scheduled sessions can't push or open pull requests (tested 17 Nov).
- **Monday phone summary:** scheduled task `trig_019nd5opsbeYkCh9jkbNAxgC`, 7:55am Melbourne, a fresh session, read-only. It reads `health-latest.md` from the `data` branch and sends a short summary (`tools/health-check.md`). Ran fine on 23 Nov.
- **Monthly audit:** `tools/audit.py` (no model). First report: `reports/audit-2026-11.md`. Every repo is behind on something; most gaps are new v1 paperwork (CLAUDE.md not pointing to STANDARDS/HANDOVER, no HANDOVER.md, charter missing `audience`/`standards`), plus 11 apps not on the shared sign-in.
- **Dashboard deploy fix:** three daily runs (20, 24, 25 Nov) failed with "No artifacts named github-pages" (GitHub timing). Upload and deploy are now separate jobs.
- **Session monitor:** private claude.ai page, refreshed on demand ("refresh the session monitor", `tools/monitor-refresh.md`).

## Decisions the owner has made (and why)
- Apps stay in separate repos. One login comes from Supabase, not from merging code. The "hubs" are groups in a shared left rail: Life, Money, Home, Workshop, Entertainment, Travel, Sport (plus Learning, Admin).
- Archive repos you give up on; don't delete.
- Lessons become standards through a `standard` issue in this repo, read by the monthly audit. The owner decides.
- Health check: option 1 (25 Nov): the report comes from a script in the daily Action, not a model.
- The monthly audit gives a report plus proposed fixes; fixes are small per-repo PRs after the owner's OK. Automatic PRs only for mechanical fixes, after about two months.
- Google Workspace API changes (email, 24 Nov): no action; usage is tiny and human-driven. Optional: check the usage dashboard before 1 Feb 2027.

## Next steps (in order)
1. After this PR merges: check the next daily run is green, and that `standard_issues` and `health-latest.md` appear on the `data` branch.
2. **Audit fixes:** propose small per-repo PRs for the mechanical gaps (CLAUDE.md pointer lines, charter `audience` + `standards`, HANDOVER.md from the template). Show the owner the list first.
3. **Left rail:** a small `kit` repo (rail, shared sign-in, theme) loaded by each app at a pinned version. **Mock it first** (nothing is built yet). Shows each person only the apps their `audience` allows (the database lock is the real security). Phones need a drawer. Open: which repo goes in which group, drawer or bottom bar, whether the App Board gets it too.
4. Add `shopping-list`, `the-big-move`, `travel-app` and `travel-planner` to the App Board.
5. Move the Monday summary to fortnightly after 4 weeks, then monthly.

## Gotchas
- Sessions can't call `api.github.com` (403) or reach `jcm-book-library.github.io`. Read dashboard data from the `data` branch with git; public repos clone fine. `audit.py` works that way.
- Scheduled sessions: no connectors, no `add_repo`, no session tools; they can't push.
- A new session starts from `main`, so a handover only helps once its PR is merged.
- Our Library is at `ourlibrary.au` and keeps a separate sign-in (D6). Its `HANDOVER.md` is 2,850 words (D7: trim). The `@ourlibrary.au` address in it is a public contact: leave it (owner, 25 Nov).
- A9 can't find the Supabase schema name in `my-book-library` and `the-brain`; check by hand.
- Recall Arcade's handover is `docs/HANDOVER.md`, not at the top level.
- Never put the owner's email, Google project ids, or session titles and summaries in this public repo.
- This checkout tracks only `main`: after pushing a new branch, add its fetch refspec or a stop hook will say it is unpushed.

## Open questions for the owner
- D2 to D5, D7 and D8 take the recommendations unless the owner says otherwise.
- House rule proposal: Claude sessions reach Google Sheets only through the connectors, never by calling the Sheets API from a script (fits Google's new MCP rule).
- Sports Tracker: once on Supabase, should each competition be a row of data instead of its own Google Sheet?

## Files that matter
- `tools/audit.py`, `reports/audit-2026-11.md`, `reports/baseline-2026-11-16.json`: the audit.
- `tools/health.py`, `tools/health-check.md`: daily report and Monday summary.
- `tools/collect.py`, `.github/workflows/collect.yml`: the dashboard data.
- `STANDARDS.md`, `plans/SUPABASE.md`.

## Start the next session with
> Repo: control-room. Task: mock the left rail (kit repo) for sign-off. Size: one stage. Done when: a mock at phone and laptop width is published as a private page and the open rail questions are answered. Read CLAUDE.md and HANDOVER.md first.
