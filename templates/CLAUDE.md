# App Name: notes for Claude

**Read the house rules first:** [HOUSE-RULES.md](https://github.com/jcm-book-library/control-room/blob/main/HOUSE-RULES.md) in `control-room` (plain text: https://raw.githubusercontent.com/jcm-book-library/control-room/main/HOUSE-RULES.md). They cover Google Sheet safety, branches and pull requests into `main`, using cheaper models to save usage credits, and the build template. The notes below are this repo's own; where they are more specific, they win. The project charter is `project.json`.

## This repo

- Source: `app.html`. Rebuild `index.html` with `python3 tools/build-pages.py` after every change and commit both.
- Live site: https://jcm-book-library.github.io/repo-name/ (from `main`).
- Sister app to Jackets & Manuscripts (`my-book-library`); copy its patterns and styles.

## Google Sheet

- Sheet: "Sheet name" (id in the owner's settings, not here if the repo is public).
- Only touch these tabs: `🆕` and tabs whose names start with 🆕.
- Columns: `id | ...` (`id` is a permanent number; new row = highest id + 1).
