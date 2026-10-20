# Templates for new repos

Copy these into a new repo, then change the placeholders (`App Name`, `repo-name`, `🆕`).

| File | What to change |
|---|---|
| `tools/build-pages.py` | `SHORT_NAME` at the top |
| `manifest.webmanifest` | `name`, `short_name`, `description` |
| `project.json` | Every field (see the house rules, section 5) |
| `CLAUDE.md` | Title, live link, sheet name and tabs |

Also add `app.html` (no `<head>`), `icons/` (`favicon-32.png`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`) and a README. Then turn on Pages: Settings → Pages → Deploy from a branch → `main`, `/ (root)` → Save.
