# Control Room: notes for Claude

**Read the house rules first:** `HOUSE-RULES.md` in this repo. Every other repo's CLAUDE.md points to it, so changes here change how every session works: keep it short, and tell the owner what changed.

## This repo

- `HOUSE-RULES.md`: shared rules for all repos.
- `templates/`: starter files for a new repo.
- `site/`: the dashboard (static HTML). `tools/collect.py` gathers public repo data into `site/data/repos.json`.
- `.github/workflows/collect.yml` runs daily, on manual run and on every push to `main`, then publishes `site/` to GitHub Pages (Pages source: GitHub Actions). Data is never committed.
- `reports/health-latest.md`: written by the weekly health check (through a pull request); the dashboard shows it.
- No Google Sheets, no sign-in: the dashboard reads public GitHub data only.
