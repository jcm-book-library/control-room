# Weekly health check

Run by a scheduled task every Monday at 7:55am Melbourne time, as a fresh session. **Nobody is watching it run, so don't ask questions.** The owner is not a coder: plain Australian English, action items first, exact clicks.

This is the *weekly* check: facts about the repos, plus a look at the owner's sessions. The *monthly audit* (checking repos against `STANDARDS.md`) is separate.

## Rules

- **Read-only everywhere**, except one pull request into `control-room` that adds `reports/health-latest.md`, and only when the check finds something. Never merge it.
- **`control-room` is a public repo.** The report holds public repo facts only: no emails, ids, keys, or anything from the owner's sessions (titles and summaries are private).
- Never put model names in commits or PRs.
- If an action is refused (for example, push access to `control-room`), don't work around it. Say what was blocked in the final message and give the report text there instead.

## 1. Read the facts

1. Clone `control-room` (`GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/jcm-book-library/control-room`) and read `CLAUDE.md`.
2. Read the dashboard data, which the daily run saves on the `data` branch:
   `git clone --depth 1 --branch data https://github.com/jcm-book-library/control-room /home/user/cr-data`, then `repos.json`.
3. If the `data` branch doesn't exist, or `generated_at` is more than 3 days old, or the file has an `error` field: that is a **Needs you** finding ("the daily dashboard run is failing: open control-room, Actions, Collect repo data and publish"). Carry on with whatever data you have.
4. The list of repos known on 16 Nov 2026 is in `reports/baseline-2026-11-16.json` (`repos[].repo`). Use it to spot new repos.

Fields in `repos.json` per repo: `name`, `html_url`, `default_branch`, `pushed_at`, `main.exists`, `latest_run` (`conclusion`, `html_url`, `name`), `pages`, `pull_requests` (`count`, `items[]` with `title`, `html_url`, `created_at`, `draft`), `health[]` (plain-words problems), `days_quiet`, `quiet` (over 30 days), `dormant` (over 90 days), `charter` and `charter_missing`. Top level: `generated_at`, `repos`, `ideas[]`, optional `error`.

## 2. Findings

Work out dates with Python (`python3 -I`), not by eye.

**Needs you** (the owner has to do something):
- A repo whose default branch is not `main`, or that has no `main` (`health` says so). Fix: repo Settings, General, Default branch.
- A pull request open more than 7 days that is not a draft. Fix: merge it or close it. Give the link.
- The latest run on `main` failed. Give the link.
- A repo that is not in the baseline list and not archived, with no charter. Fix: give it `project.json`, a `CLAUDE.md` that points at the house rules, and a README (see `templates/`).
- The data problems in step 1.3.

**Worth a look:**
- A repo quiet for over 90 days (`dormant`): suggest setting its stage to Paused, or archiving it.
- Any other `health` message (for example a Pages mismatch).

**Good to know:**
- Quiet 30 to 90 days (names only).
- Totals: repos, open PRs, open `idea` issues, and the three newest idea titles (ideas are public).

Don't list charter or standards gaps here. The monthly audit does that.

## 3. The owner's sessions (private: final message only, never in the repo)

Use `list_sessions` and `get_session` if you have them. Skip archived sessions and this one.
- **Waiting on the owner for more than 5 days:** title, how long, and what it needs in a few words.
- **Context at or over 50%** (`external_metadata.context_usage.used_tokens` out of `max_tokens`): title and the percentage. Suggest handing over: ask it to rewrite `HANDOVER.md`, then start a fresh session.

If you can't see sessions, say so in one line.

## 4. Output

- **If there is anything under Needs you or Worth a look:** write `reports/health-latest.md` (below), on a new branch `claude/health-YYYY-MM-DD` in `control-room` (use `add_repo` with push access if needed), commit, push, and open a pull request into `main` titled `Health check YYYY-MM-DD`. In the PR, say in plain words that it only replaces the health panel on the dashboard. Don't merge it.
- **If everything is fine:** no pull request. Say "All clear" in the final message.

**`reports/health-latest.md` format** (plain text, short lines; the dashboard shows it as is):

```
Health check, Mon 23 Nov 2026
Data from the daily run on 23 Nov 2026.

NEEDS YOU
- travel-app: default branch is claude/..., not main. Fix: repo Settings, General, Default branch.
- tv-tracker: pull request open 9 days: <title> <link>

WORTH A LOOK
- game-tracker: no activity for 112 days. Pause it or archive it?

GOOD TO KNOW
- 20 repos, 3 open pull requests, 4 open ideas. Quiet for 30 to 90 days: household.
```

## 5. Final message (the only place the owner reads this)

Under 250 words:
1. **Do this first:** the Needs-you items as numbered steps with exact clicks and links (or "Nothing needs you").
2. **Sessions:** the private items from step 3.
3. **Worth a look and good to know**, one line each.
4. One line saying whether a pull request was opened (with the link) and anything you couldn't check.
