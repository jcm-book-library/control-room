# App Name: notes for Claude

**Read first:** [HOUSE-RULES.md](https://github.com/jcm-book-library/control-room/blob/main/HOUSE-RULES.md) (how to work: Google Sheet safety, branches and pull requests into `main`, using cheaper models, the build template; plain text: https://raw.githubusercontent.com/jcm-book-library/control-room/main/HOUSE-RULES.md) and [STANDARDS.md](https://github.com/jcm-book-library/control-room/blob/main/STANDARDS.md) (what every repo and app should have), both in `control-room`. Then read `HANDOVER.md` in this repo: it is where the last session left off. The notes below are this repo's own; where they are more specific, they win. The project charter is `project.json`. Keep this file under 400 words; put reference material in `docs/`.

## This repo

- Source: `app.html`. Rebuild `index.html` with `python3 tools/build-pages.py` after every change and commit both.
- Live site: https://jcm-book-library.github.io/repo-name/ (from `main`).
- Sister app to Jackets & Manuscripts (`my-book-library`); copy its patterns and styles.

## Google Sheet

- Sheet: "Sheet name" (id in the owner's settings, not here if the repo is public).
- Only touch these tabs: `🆕` and tabs whose names start with 🆕.
- Columns: `id | ...` (`id` is a permanent number; new row = highest id + 1).

## Finishing a session

Before you stop: run the tests and the build, rewrite `HANDOVER.md` (don't add to it), open the pull request into `main`, and say what changes on the live site. Then ask the owner: **did we learn something every app should do?** If yes, open an issue in `control-room` labelled `standard` saying what, which app and why.
