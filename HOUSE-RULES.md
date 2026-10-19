# House rules

Shared rules for every repo in `jcm-book-library`. Each repo's `CLAUDE.md` points here and adds only what is special about that repo. Where a repo's own notes are more specific, they win.

## The owner

- One person, not a coder, with ADHD. Put their action items first, keep steps short, and say exactly what to click.
- They like options with a recommendation, bullet points first, and pushback. They don't need agreement.
- Lives in Melbourne. Australian English, Australian measures, °C, dates shown as `19 Oct 26` in apps (sheets store real dates).

## 1. Google Sheet safety (non-negotiable)

Most apps read and write a Google Sheet. The sheet is the real data; the app and the browser copy are not.

- **Stay in your lane.** Each app owns only the tabs listed in its `CLAUDE.md` or README, usually marked with its emoji (📺, 🎥, 🎮, 🎸 …). Never read or write another app's tabs. In the shared "Entertainment Tracker" sheet, never touch Books, Reading Log, App Settings, Ratings, Contents, Wishlist, Calibre Review or any backup tab unless you are working in `my-book-library`.
- **Scope every call** to a range inside your own tabs. No whole-sheet reads or writes.
- **Back up first.** Before any bulk change or column change, make a dated backup tab (`📺 backup 2026-10-18`) and never write to it afterwards.
- **Find, then write.** Find the row by its `id` right before every write, require exactly one match, and write only the cells that changed. Never rewrite whole tabs, never delete and re-add rows, never sort the sheet from code.
- **Permanent ids.** Every row has a permanent number `id`. New row = highest id + 1, re-read just before appending. Never renumber, never a formula.
- **Formats.** Dates `yyyy-mm-dd`, numbers as numbers, text prefixed with `'`. No formula columns in app-owned tabs.
- **Keep dropdowns.** Any data-validation change sets `customUiMode: CHIP` so dropdowns stay as chips.
- **Check afterwards.** After any bulk change, read the tab back and compare it with a script. Never hand-type long arrays into tool calls.
- **Only the lead session writes.** Subagents never write to a sheet. Show the owner the plan before the first write of a session.
- **Keep links private.** Sheet links and ids go in the owner's settings (in the sheet or the browser), not in public code, unless that repo already documents otherwise. All sheets are set to Restricted.

## 2. Branches and pull requests

- `main` is the live site (GitHub Pages publishes from it) and is the default branch in every repo.
- Work on a branch, never directly on `main`. Commit and push each finished stage.
- Reach `main` through a pull request the owner merges. Say in the PR, in plain words, what will change on the live site.
- Before opening the PR: run the repo's build (if any) and its tests, and re-read your own diff.
- Session branches (`claude/...`) are left alone after merging; don't delete them unless asked.
- The only things that write to `main` without a PR are scheduled GitHub Actions that refresh data (daily-paper, investments prices), and only their data files.

## 3. Using models (to save usage credits)

The owner wants work split so the strongest model is spent only where it adds value.

| Who | Does |
|---|---|
| **Lead session** (strongest model) | Planning, data-model and design decisions, sheet-safety decisions, anything that writes to a Google Sheet, tricky logic (sync, conflicts), reviewing every subagent's output before it's committed, talking to the owner |
| **Sonnet subagents** | Building a feature from a written spec, porting patterns between apps, routine edits across repos, writing and running Playwright tests, fixing test failures |
| **Haiku subagents** | Mechanical work: searches, file sweeps, look-ups, read-back comparisons, lint passes, checking screenshots for sideways scrolling |

- Give each subagent a self-contained brief: files, the exact change, the rules that apply, and what "done" looks like. Ask for a short result, not file dumps.
- One well-scoped subagent beats several overlapping ones. Fan out only when the parts are truly independent.
- Say in the reply which parts were delegated, and to which model.
- Never put model names in commits, code, docs or PRs.

## 4. Build template (single-file apps on GitHub Pages)

Most apps share one shape. Start new ones from `control-room/templates/`.

| File | What it is |
|---|---|
| `app.html` | The only source. No `<head>`, so the same file can be published as a claude.ai artifact. |
| `index.html` | Built from `app.html` by `python3 tools/build-pages.py`. Never edit it by hand; commit it with `app.html`. |
| `tools/build-pages.py` | Adds the doctype, meta tags, icons and manifest. |
| `manifest.webmanifest`, `icons/` | Home-screen install. Icons: `favicon-32.png`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`. |
| `project.json` | The charter (see below). |
| `CLAUDE.md` | Points here, then this repo's own notes. |
| `README.md` | What it does, live link, files, sheet tabs, how to run. |

- **Look:** shared with Jackets & Manuscripts (`my-book-library`): Proton Seasons tokens, Atkinson Hyperlegible + Figtree, dark.
- **Scripts** only from cdnjs (pinned versions), fonts only from Google Fonts, everything else inline.
- **Google sign-in on Pages** reuses the book app's OAuth Client ID (saved in the browser as `mbl_config`). Each app keeps its own localStorage keys with its own prefix.
- **Testing:** headless Playwright with Chromium at `/opt/pw-browsers/chromium` and a stubbed `window.claude`, at 390px and 1280px wide, before every publish. No sideways scrolling.
- Apps with a different build (recall-arcade on Vite, daily-paper and investments built by Actions) keep their own setup and say so in their README.

## 5. Charter: `project.json`

Every repo has one at its root. The Control Room dashboard reads it from `main`; a repo without one is flagged as new.

```json
{
  "name": "TV Tracker",
  "repo": "tv-tracker",
  "purpose": "One plain sentence: what it does and where its data lives.",
  "family": "Entertainment",
  "stage": "Building",
  "live": "https://jcm-book-library.github.io/tv-tracker/",
  "tags": ["media-tracker"],
  "updated": "2026-10-19"
}
```

- **family:** Entertainment, Life, Home, Finance, Hobby, Learning or Admin.
- **stage:** Idea, Planning, Building, Working, Mature or Paused.
- **live:** the GitHub Pages link, or `null` if there's no app yet.
- **tags:** `media-tracker` marks the five media trackers (books, TV, albums, games, films).
- Update it when the project changes direction or stage.

## 6. Privacy (the repos and sites are public)

- No email addresses, passwords, API keys, sheet links, personal figures or private photos in the repo.
- Logos, photos and other private files live in the owner's Google Drive and load after Google sign-in.
- If something private is found in a repo, tell the owner first; removing it from history needs their go-ahead.

## 7. Ideas and the Control Room

- Ideas are GitHub issues labelled `idea`, in whichever repo they belong to. The dashboard lists them.
- Dashboard: https://jcm-book-library.github.io/control-room/ (refreshed daily).
- A new repo appears on the dashboard the next day. Give it a `project.json`, a `CLAUDE.md` that points here, and a README.
