# Plan: moving the apps to Supabase

Status: plan only, nothing migrated. Written 19 Oct 2026.

## In short

- **One Supabase project** for every app, one schema (folder of tables) per app, and Google sign-in so only you can read or write.
- **Pilot: TV Tracker.** It has a clean id column, a one-row-per-episode log The Brain wants, and a 53-check smoke test to prove nothing broke.
- **Google Sheets stay** as a read-only archive, plus a weekly export back to a backup sheet so you can still browse your data in Sheets.
- **The Brain** then reads one shared "activity" view instead of reaching into five different sheets.

## 1. One project for all apps

| Piece | Choice | Why |
|---|---|---|
| Project | One, e.g. `jcm-apps`, Sydney region | One sign-in, one bill, and The Brain can read across apps |
| Tables | One schema per app: `tv`, `books`, `albums`, `games`, `films`, `brain`, `pantry` … | Same "stay in your lane" rule as the sheet tabs today |
| Shared | Schema `shared` holding the `activity` view (below) | The only place apps meet |
| Sign-in | Supabase Auth with Google | Same Google account you use now |
| Security | Row Level Security on every table: only your user id can read or write | The public key in the app code is then safe in a public repo |
| Plan | Free tier to start | Caveat: free projects pause after 7 days without use. The daily Control Room run can ping it to keep it awake |

The house rules carry over: permanent ids, dates as real dates, no bulk rewrites from the app, a backup before any change of shape.

## 2. Pilot: TV Tracker

Recommended because its data model is the most settled and best tested. Alternative: build Game Tracker on Supabase from day one, since it has no data yet; that tests a new app but not a migration.

1. Create the project and the `tv` schema: `shows`, `log`, `seasons`, `quotes`, `settings`, matching today's 📺 tabs column for column.
2. Copy the data once with a script; read it back and compare row counts and ids with the sheet.
3. Add a Supabase mode to the app beside the Sheets mode, switched in Settings. Run both for two weeks; the smoke test runs against each.
4. Switch over: the app writes only to Supabase. The 📺 tabs get a note in A1, "Moved to Supabase on <date>", and are no longer written.
5. Review after a month: speed, offline use, anything missed. Then decide on the next app.

Order after the pilot: Albums, then Books (largest and most used, so it goes once the pattern is proven), then Games and Films, then the rest.

## 3. What happens to the Google Sheets

- **Nothing is deleted.** Each tab is frozen at its switch-over date and kept as an archive.
- **Weekly export:** a GitHub Action copies each Supabase table to a backup Google Sheet (new dated tab each time, last 8 kept). This is your "open it in Sheets" view and an off-Supabase backup.
- **claude.ai artifacts** use the Google Sheets connector today. During the pilot they keep reading the sheet; after switch-over they read the backup sheet (read-only) or a Supabase connector if you add one.
- Apps not yet moved keep working exactly as now.

## 4. How The Brain reads logs

A view `shared.activity` stacks every app's log in one agreed layout, the one the survey recommended:

`date | app | item_id | title | amount | unit | logged_at | source | note`

| App | amount / unit |
|---|---|
| Books | pages |
| TV | episodes |
| Albums | plays |
| Games | minutes |
| Films | watches |

The Brain reads this view only (never writes to other apps). Its Pages, Episodes and similar columns fill themselves from the view, and a number you typed yourself is never overwritten. Each app joins the view as it moves, so The Brain gains books first if Books moves before others.

## Decisions for you

- [ ] OK to create one Supabase project (free tier) under your Google account?
- [ ] Pilot app: TV Tracker (recommended) or Game Tracker built fresh?
- [ ] Weekly export back to a backup Google Sheet: yes or no?
