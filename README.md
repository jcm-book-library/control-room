# Control Room

One place to see every project in `jcm-book-library`.

- **Dashboard:** https://jcm-book-library.github.io/control-room/ (refreshed every morning)
- **House rules:** [HOUSE-RULES.md](HOUSE-RULES.md), shared by every repo
- **Starting a new repo:** copy [templates/](templates/)

## What the dashboard shows

- A card per repo, grouped by family (from each repo's `project.json`)
- Entertainment: quick links to the five media trackers
- Needs attention: problems with `main`, new repos without a charter, quiet projects
- Ideas: issues labelled `idea` in any repo
- The latest weekly health check

## How it updates

A GitHub Action (`.github/workflows/collect.yml`) runs every morning at about 6:17am Melbourne time, collects public data about each repo, and publishes the site. To refresh it now: **Actions** tab → **Collect repo data and publish** → **Run workflow**.
