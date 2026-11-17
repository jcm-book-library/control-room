# Standards (version 1)

Version 1, 16 Nov 2026. Written from the 20 repos as they stood that day.

`HOUSE-RULES.md` says **how to work** (Sheet safety, branches, models, privacy). This says **what every repo and app should have and do**. The planned audit checks these; anything new we learn goes in through section 5.

- **Check** column: *auto* means a script can check it, *manual* means someone has to look.
- Where we stand today is in section 6. Questions for the owner are in section 7. Each has a recommendation that becomes the standard when this is merged.

## 1. Every repo (R)

| ID | Standard | Check |
|---|---|---|
| R1 | The default branch is `main`. Work happens on a branch and reaches `main` by pull request. | auto |
| R2 | `CLAUDE.md`: 400 words or fewer. It points to `HOUSE-RULES.md`, `STANDARDS.md` and `HANDOVER.md`, then lists only what is special about this repo. | auto |
| R3 | `README.md`: what it does, the live link, the files, how to run and test it. | auto |
| R4 | `project.json` (the charter) has every field below. | auto |
| R5 | `HANDOVER.md`: 800 words or fewer, **rewritten at the end of each session, not added to**. Template in `templates/HANDOVER.md`. | auto |
| R6 | Reference material (column lists, schemas, long history) lives in `docs/`, not in `CLAUDE.md` or `HANDOVER.md`. | manual |
| R7 | No emails, passwords, secret keys or personal figures. No new sheet or project ids in code (existing ones leave when the app moves to Supabase). Supabase publishable keys are fine. | auto + manual |

**Charter fields (`project.json`):** `name`, `repo`, `purpose`, `family`, `stage`, `live`, `tags`, `audience`, `standards`, `updated`.

- `stage`: Idea, Planning, Building, Working, Mature, Paused. (Archived repos leave the dashboard.)
- `audience`: `owner` (only you), `family`, `partner` or `public`. This decides who the left rail shows an app to and which Supabase lock it gets.
- `standards`: the version of this document the repo was last brought up to (now `1`). The audit compares it with the current version.
- `family`: see D2.

## 2. Every app (A)

| ID | Standard | Check |
|---|---|---|
| A1 | **Build.** Source is `app.html`. `index.html` is built by `tools/build-pages.py`, copied from `templates/tools/`. The only edits allowed are the three settings at the top (`SHORT_NAME`, `THEME_COLOUR`, `LANG`). An app with a different build says so in its README. | auto |
| A2 | **Home screen.** Any app used on a phone has `manifest.webmanifest` and icons: `favicon-32.png`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`. | auto |
| A3 | **Look.** The shared colour tokens in `:root` (`--bg --surface --raise --line --fg --muted`, plus an accent), dark, month colours. Font: Roboto for all new and rebuilt apps (D1); existing apps switch when they are rebuilt or get the rail. | auto (tokens) + manual |
| A4 | **Tests live in the repo**, and the README or `tests/README.md` says how to run them. They run before every pull request. An app that writes data has a test against a fake of its data store. | auto + manual |
| A5 | **Phone first.** Works at 390 px and 1280 px wide with no sideways scrolling. | manual (test) |
| A6 | **Scripts** only from cdnjs with pinned versions. **Fonts** only from Google Fonts. Everything else is inline. | auto |
| A7 | **Data.** A new app starts on Supabase. Existing apps move in the order in `plans/SUPABASE.md`. Until then they follow the Sheet safety rules (HOUSE-RULES section 1). | manual |
| A8 | **Sign-in.** Supabase email code, with a password option for phones, using the shared session key `jcm-sb-session`. No hourly Google reconnect once an app has moved. | auto |
| A9 | **Access.** On Supabase, the app's schema is on the owner-only list (`supabase/owner-only.sql`) unless the app is meant for family (`books`, `family`). | auto |
| A10 | **Left rail.** The shared menu from the kit. Reserved for standards version 2. | auto (later) |

## 3. Media trackers (T)

Books, TV, films, albums, games, and any future tracker. Same shape, each in its own words.

| ID | Standard |
|---|---|
| T1 | Every tracker has `id`, title, status, rating, `Plan`, `Up next #`, `Why` and notes. |
| T2 | **Plan** is one column called `Plan` with the values `Up next`, `Soon`, `Someday`. Order goes in `Up next #`. `Why` is one line. (Games store it as `Tier` and books as `tier`: change the stored name when the app moves, show `Plan` to the owner now.) |
| T3 | **Status words** differ by medium, but every tracker maps to the same categories (table below). |
| T4 | **Ids** are permanent numbers. A new id is the highest one plus 1 within that app. Never renumber. They only need to be unique inside an app, because the app name travels beside them (as in `shared.activity`). Exceptions: books use +4 (a convention since the first version) and albums use ranges from 1000 and 7000. |
| T5 | **Log:** one log per tracker, laid out `date, itemId, title, amount, loggedAt, source, note`, plus extra columns where the medium needs them (TV adds season and episode). The unit differs (pages, episodes, plays, minutes, watches). Today each log differs a little, and `shared.activity` maps them. |
| T6 | A `Settings` tab (`key, value`), and a dated backup tab before any column or bulk change. Supabase equivalents once an app moves. |
| T7 | Ownership or format is its own column, never a status. |

| Category | Books | TV | Films | Albums | Games |
|---|---|---|---|---|---|
| Waiting | TBR | Watchlist, Coming Soon | Watchlist, Coming Soon | Listen, Purchase, Coming Soon | Playlist, Coming Soon, In Development |
| Next (also set `Plan` = Up next) | (Plan only) | Next Up | Next Up | (Plan only) | Next Up |
| In progress | Reading | Watching | Watching | n/a | Playing |
| Done | Finished | Watched | Watched | Listened | Played |
| Again | Re-read | Rewatch | Rewatch | n/a | Replay |
| Paused | Paused | Paused | missing | n/a | Paused |
| Dropped | DNF | DNF | missing | Didn't like | DNF |

Gaps to close when each app is next touched: films have no Paused or DNF; albums keep `Owned` in Status, which breaks T7 (D4). Albums' `Listen` and `Purchase` are read here as "waiting"; check that is what you mean by them.

## 4. Sessions (S)

A session is one chat. Its memory fills up and it gets slower, more expensive and more error-prone, so sessions stay short and the *repo* carries the memory.

| ID | Standard |
|---|---|
| S1 | One repo per session, one piece of work per session. Control Room is the exception: it works across repos. |
| S2 | **Start a new session** at about 50% context; after each merged stage or big change; when you switch repo or topic; after a week idle; or when it repeats itself, forgets a decision or makes simple mistakes. Under 40% is fine to carry on. 40 to 60% means finish the task and hand over. Over 60% means hand over now. |
| S3 | Reusing a session for a tiny tweak is fine if it is under 30% and the same day. |
| S4 | `CLAUDE.md` is read automatically. It sends the session to `HANDOVER.md`, so you do not paste handovers. |
| S5 | The owner should not be asked what is already in the repo. |

**Start prompt** (copy, fill in the brackets):

```
Repo: [name]. Task: [one sentence].
Size: [small tweak | one stage | big change].
Done when: [what you'll check].
Read CLAUDE.md and HANDOVER.md first, tell me in 5 lines where things stand, and wait for my OK before anything big. Don't ask me things you can find in the repo.
```

**Finish prompt** (paste at the end of any session; then **merge the pull request it opens before starting the new session**, because a new session starts from `main` and can't see an unmerged handover):

```
Wrap up this session.
1) Run the tests and the build.
2) Rewrite HANDOVER.md (where we are, what changed, decisions, next steps, gotchas, open questions) and commit it with the work.
3) Open the pull request into main and tell me what changes on the live site.
4) Did we learn anything every app should do? If yes, say what.
5) Give me one short message to start the next session.
```

## 5. Lessons become standards (L)

Apps drift when something learned in one is not carried to the others. The fix is a written place for lessons.

1. **Ask the question.** At the end of every big change (step 4 of the finish prompt): *did we learn something every app should do?* A new layout, a new requirement, a trap that bit us.
2. **Write it down once.** If yes, open an issue in `control-room` labelled `standard`: what we learned, which app, why every app should do it. (You can add one from your phone, like an idea.)
3. **The monthly audit reads the open `standard` issues** and brings the ones worth adopting to you. You decide.
4. **If adopted**, it goes into this file with a new version number and a dated line in the changelog below. The audit then shows which apps are behind.
5. **Fixes** reach the apps as small pull requests, one per repo. Anything that changes how an app looks or behaves is shown to you first.

## 6. Where we stand today (baseline, 16 Nov 2026)

Counts are repos out of 20. The audit uses these as its starting line.

| Standard | Meets it | Gaps |
|---|---|---|
| R1 default branch `main` | 17 | `shopping-list`, `travel-app` and `travel-planner` had a `claude/` branch as their default. `main` now exists in all three (16 Nov), but their default branch still needs switching in GitHub settings. |
| R2 `CLAUDE.md` points to the rules, 400 words or fewer | 15 | Over 400 words: `travel-app` (1600), `travel-planner` (1252), `sports-tracker` (1092), `tv-tracker` (557), `the-brain` (481). All 20 already point to the house rules. |
| R4 charter has every field | 0 | All 20 have the 8 old fields. `audience` and `standards` are new. |
| R5 `HANDOVER.md` at the root | 1 | Only `my-book-library` (3,500 words: too long, it holds reference material). `recall-arcade` has `docs/HANDOVER.md` and `sports-tracker` has `docs/handoff-formula-e.md`. |
| R7 no ids in public code | 11 | Sheet or project ids in code: `Bag-and-Tag`, `Pantry-Plate`, `Sawdust-Soil`, `game-tracker`, `investments`, `my-book-library`, `sports-tracker`, `the-brain`, `tv-tracker`. No secret keys found anywhere. |
| A1 build script matches the template | 0 of 13 with one | Every copy differs. The template is newer: it has the three settings at the top and a check that stops a stray `<head>`. `investments`, `daily-paper`, `recall-arcade`, `the-brain`, `control-room` and the two travel repos have no build script. |
| A2 home-screen install | 14 | Missing a manifest: `the-brain`, `daily-paper`, `recall-arcade`, `control-room`, and the two travel repos (no app yet). `Bag-and-Tag` is the only app with an offline service worker. |
| A3 shared colour tokens | at least 6 | Same token names confirmed in books, TV, games, budget, pantry and household (8 apps were checked). Fonts differ (D1). |
| A4 tests in the repo | 12 | None found in `Bag-and-Tag`, `Pantry-Plate`, `Personal-budget`, `Sawdust-Soil`, `game-tracker`, `recall-arcade`, and the two travel repos. Where tests exist, every repo says how to run them. |
| A8 shared Supabase session | 2 | `my-book-library` and `the-brain`. 13 other apps still sign in with Google only and reconnect hourly. |

## 7. Decisions for the owner

Each recommendation becomes the standard when this pull request is merged. Say so if you want any of them different.

| ID | Question | Recommendation |
|---|---|---|
| D1 | **Fonts.** The house rules said Atkinson Hyperlegible + Figtree (6 apps). Books and the shopping list now use Roboto. | **Decided 16 Nov 2026: Roboto for all new and rebuilt apps.** Existing apps keep their font until they are rebuilt or get the rail. HOUSE-RULES section 4 updated. |
| D2 | **Families** in `project.json` today: Entertainment, Life, Home, Finance, Hobby, Learning, Admin. The left rail will group differently. | Match the rail: Life, Money, Home, Workshop, Entertainment, Travel, Sport, plus Learning and Admin. So Finance becomes Money and Hobby becomes Workshop. |
| D3 | **Status words** (section 3). | Keep each medium's own words. Add the missing ones (films: Paused, DNF) when each app is next touched. |
| D4 | **Albums keep `Owned` in Status.** | Leave until Albums moves to Supabase, then split it into its own column (T7). |
| D5 | **Sheet ids in public code** (9 repos). | No new ones. Existing ones go when each app moves to Supabase. Do not scrub now. |
| D6 | **One sign-in across the rail.** Our Library is now at `ourlibrary.au`. Sign-in storage is per address, so it cannot share a session with the apps on `jcm-book-library.github.io`. | **Decided 16 Nov 2026: accept a separate sign-in for Our Library** (it is the family-facing app anyway). The rail links out to it. Revisit if you later want every app under one address. |
| D7 | **Size caps:** `CLAUDE.md` 400 words, `HANDOVER.md` 800 words. | Yes. Move the rest to `docs/`. The Library's handover is the first to trim. |
| D8 | **Tests required** for an app that writes data (5 have none: `Bag-and-Tag`, `Pantry-Plate`, `Personal-budget`, `Sawdust-Soil`, `game-tracker`). | Yes, added when each app is next touched, not in one sweep. |
| D9 | **Three repos have no `main`** (`shopping-list`, `travel-app`, `travel-planner`). They are ideas that never reached the point of merging into `main`. | **Decided 16 Nov 2026: create `main` now.** Done the same day in `travel-app` and `travel-planner` (`shopping-list` already had one). Still to do: switch each repo's default branch to `main` in GitHub settings. |

## Changelog

- **v1, 16 Nov 2026.** First written from the 20 repos as they stood. Sections R, A, T, S and L; decisions D1 to D9.
- **17 Nov 2026, clarification (no version change).** D1, D6 and D9 decided. Finish prompt: merge the handover's pull request before starting the new session.
