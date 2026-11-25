# Control Room: notes for Claude

**Read the house rules first:** `HOUSE-RULES.md` in this repo. Every other repo's CLAUDE.md points to it, so changes here change how every session works: keep it short, and tell the owner what changed.

## This repo

- `HOUSE-RULES.md`: shared rules for all repos.
- `templates/`: starter files for a new repo.
- `site/`: the dashboard (static HTML). `tools/collect.py` gathers public repo data into `site/data/repos.json`.
- `.github/workflows/collect.yml` runs daily, on manual run and on every push to `main`, then publishes `site/` to GitHub Pages (Pages source: GitHub Actions). Data is never committed to `main`: the daily run saves one copy on the `data` branch (a single commit, replaced each day) so sessions can read it with git.
- `tools/health.py`: writes the daily health report (`health-latest.md`) in the same Action; the dashboard shows it and it is saved on the `data` branch. A Monday scheduled task sends a phone summary of it (`tools/health-check.md`).
- `tools/audit.py`: the monthly standards audit. Run it in a session ("run the monthly audit"); it writes `reports/audit-YYYY-MM.md`.
- No Google Sheets, no sign-in: the dashboard reads public GitHub data only.
