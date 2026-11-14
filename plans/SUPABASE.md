# Plan: moving the apps to Supabase

Status: **The Brain is switched over and in daily use on Supabase. Books (The Library) is moving now.** Updated 14 Nov 2026 (first written 19 Oct 2026). Every other app is still on its Google Sheet.

## Next steps for Books (in order)

Books follows the same recipe as The Brain (section 2). The SQL is in `supabase/` in my-book-library; Claude gives it to you to paste.

1. **Create the tables** (Supabase, 2 minutes): SQL Editor, **+ New query**, paste the schema SQL, **Run**, then **Run and enable RLS** in the warning box (a false alarm).
2. **Create the shared view** (1 minute): paste the `shared.activity` SQL, **Run** (section 6).
3. **Exposed schemas** (1 minute): **Integrations → Data API → Settings → Exposed schemas**, add `books` and `shared`, **Save**. Supabase doesn't do this for you.
4. **Redirect URL** (1 minute): **Authentication → URL Configuration → Redirect URLs**, add `https://jcm-book-library.github.io/my-book-library/**`.
5. **Merge the my-book-library pull request.**
6. **Laptop:** The Library, Toolbox, **Data & sign-in**, sign in with the same email and password as The Brain, **Copy Sheet → Supabase**. It checks every row afterwards and switches that device to Supabase.
7. **Phone:** the same dialog, email and password, **Sign in with password**.
8. **Say "switch over"** within a day: a tiny second pull request makes Supabase the default on every device.

Done once a week has passed with nothing missing. Then Albums can start.

## In short

- **One Supabase project** for every app (`jcm-apps`, Sydney), one schema (folder of tables) per app, and sign-in so only you can read or write.
- **The Brain went first** and is switched over. **Books is second** (your choice, ahead of Albums): it is the most used, and it feeds the shared activity view.
- **Google Sheets stay** as an archive. Each app has a **Copy Supabase → Sheet** button, used weekly, as the backup you can browse in Sheets.
- **The Brain reads one shared "activity" view** instead of reaching into five different sheets. Books is its first feed.
- **One sign-in for every app** in a browser (section 3).
- **Keep it awake.** Free projects pause after about a week without use. Daily use of switched-over apps fixes that; section 4 has a backup plan.

## 1. One project for all apps

| Piece | Choice | Why |
|---|---|---|
| Project | One: `jcm-apps`, Sydney region | One sign-in, one bill, and The Brain can read across apps |
| Tables | One schema per app: `brain` (live), `books` (moving), then `albums`, `tv`, `games`, `films`, `pantry` … | Same "stay in your lane" rule as the sheet tabs today |
| Shared | Schema `shared` holding the `activity` view (section 6) | The only place apps meet |
| Sign-in | Supabase Auth: email and password (works in phone home-screen apps), plus an email link for laptops. Sign-ups are off | Works without Google Cloud steps |
| Security | Row Level Security on every table: only your user id can read or write. Signed-out visitors get nothing | The public key in the app code is then safe in a public repo |
| Family accounts | Only Our Library (the `books` and `family` schemas) is open to family members. Every other app is locked to your account (section 8) | Family members are real accounts in the same Supabase Auth, so each private app has to refuse them itself |
| Plan | Free tier | Caveat: pauses after about a week without use (section 4) |

The house rules carry over: permanent ids, dates as real dates, no bulk rewrites from the app, a backup before any change of shape. Never put the `service_role` key or the database password in a chat, and Claude never asks for them.

## 2. The recipe (proven on The Brain, refined on Books)

Each app moves the same way. **You** do the Supabase clicks; **Claude** does the code and tests.

1. **Scan first.** Before writing the schema, Claude reads the app's tabs (read-only) and checks every column's real values: numbers stored as text (`1,116`), Yes/blank columns that are really true/false, mixed dates and words, duplicate ids. Types come from the data, not guesses.
2. **Schema.** One numbered SQL file (`01-schema.sql`): one table per tab, column for column, plus `row_id`, `user_id` (filled in from whoever is signed in) and `updated_at`; Row Level Security on with an "own rows" rule; access for signed-in users only; live sync switched on in the same file. Formula columns are not stored: the app works them out. Claude tests the SQL on a local Postgres (including the security rules) and gives it to you **to paste inline**, not as a file name.
3. **Expose the schema.** **You** add it to *Exposed schemas* in the Data API settings. Supabase doesn't do this automatically. Then **lock it to you**: add the schema name to `v_schemas` in `supabase/owner-only.sql` and run that file again (section 8). Its check at the bottom lists any app schema that is still open.
4. **Data layer first.** If the app talks to the Sheet from many places (Books did, from about 45), gather them into one set of named operations before adding Supabase, and prove nothing changed by checking every recorded Sheet write is byte-identical. The Brain already had this shape.
5. **Supabase mode beside the Sheets mode,** behind that data layer, so the screens never talk to either directly. It returns data in the same shape the Sheet does, so screen code doesn't change. Each device picks its source.
6. **Copy and check.** One button copies Sheet to Supabase, then reads Supabase back and compares every row. It refuses if the Sheet has duplicate ids. A read-only **Check** button lists every tab with its row count in each place and what differs.
7. **Copy back.** **Copy Supabase → Sheet** shows what will change, makes a dated hidden backup of each tab first, writes only the cells that differ (never formula columns), re-checks the Sheet hasn't changed, then reads it back to check. Rows removed in the app are cleared in the Sheet, never deleted.
8. **Tests.** Three headless suites run before every push: the Sheets mode, the Supabase mode (fake Supabase and fake live sync), and the copy-back.
9. **Switch over fast.** The copy switches the device it ran on; a tiny follow-up pull request makes Supabase the default everywhere within a day. The Sheet is kept as an archive.

Lessons:
- **Phone home-screen apps** keep separate storage from the browser, so an emailed *link* signs in the wrong place. A typed *password* works. Every app offers the password from day one. Each home-screen app on a phone signs in once, even with the shared session (section 3).
- **A pilot that isn't the default doesn't get used**, so the project paused. Move quickly from "side by side" to "switched over".
- **App shows 0 rows but the SQL check shows rows:** the sign-in is stale. Sign out of Supabase in the app and sign in again. The apps say this when they load nothing.
- **Tab headers live in row 1 of every Sheet tab**, so "Moved to Supabase" notes can't go in A1. Use a separate note tab, and only with your go-ahead.

## 3. Sign in once for every app

All the apps are on `jcm-book-library.github.io`, so in one browser they share storage. From Books on, every app uses **one shared session key, `jcm-sb-session`**:
- Signing in in one app signs in all of them in that browser; signing out signs out all of them.
- Supabase replaces the refresh token each time it is used, so two apps refreshing at once could sign each other out. The shared sign-in code takes a browser lock (`jcm-sb-refresh`) around each refresh and re-reads the stored session inside it.
- Phone home-screen apps each keep their own storage, so each one still signs in once with the password.
- The reference copy of the sign-in code lives in my-book-library (`sb` in `app.html`); each app pastes the same block.

**Moving The Brain onto it** (needs your go-ahead, a small the-brain pull request): switch `brain-sb-session` to `jcm-sb-session`, moving the existing session across once so you aren't signed out; add the same lock; add a test. The same pull request makes The Brain read `shared.activity` (section 6).

## 4. Keeping it awake

- Daily use of a switched-over app keeps the project awake.
- **Backup plan:** the daily Control Room run makes one harmless request to the project so it never idles for a week. It only needs the public key, and it reads nothing private. Add it only if the project pauses again; it is a small change to the Control Room workflow, through a pull request.
- If it pauses anyway, **Restore project** brings it back: dashboard, **jcm-apps**, **Restore project**, wait a few minutes. If there is no restore button, tell Claude before doing anything else; the Sheets still have everything up to their last copy-back.

## 5. What happens to the Google Sheets

- **Nothing is deleted.** Each tab stays as an archive.
- **Backup:** each app's **Copy Supabase → Sheet** button, weekly, is the off-Supabase backup and your "open it in Sheets" view. (A weekly GitHub Action export was considered and deferred: the button covers it for now.)
- **claude.ai artifacts:** Books' artifact is frozen read-only (you use the live site), so it can't drift from Supabase. Other apps decide as they move.
- Apps not yet moved keep working exactly as now.

## 6. How The Brain reads other apps

A view `shared.activity` stacks every app's log in one agreed layout:

`date | app | item_id | title | amount | unit | logged_at | source | note`

| App | amount / unit | Status |
|---|---|---|
| Books | pages | View created with Books (`supabase/03-shared.sql` in my-book-library) |
| TV | episodes | When TV moves |
| Albums | plays | When Albums moves |
| Games | minutes | When Games moves |
| Films | watches | When Films moves |

- Books' feed is its Reading Log, skipping deleted entries and 0-page rows. Pages include Kobo's inflated counts, so The Brain shows the same numbers as the book app's daily chart.
- The view runs as the signed-in user (`security_invoker`), so every table's "own rows" rule still applies. Each app joins with `union all` when it moves.
- The Brain reads this view only (never writes to other apps). Its Pages figure fills itself from the view, and a number you typed yourself is never overwritten. Until The Brain's pull request, pages are typed by hand.

## 7. Order

1. **The Brain**: switched over.
2. **Books**: moving now (steps at the top).
3. **Albums**: small, so a quick third.
4. **TV Tracker**: cleanest id column and a 53-check smoke test, so a low-risk move.
5. **Games and Films**, then the rest.

## 8. Owner-only apps (before family members join)

Family members will be real accounts in the same Supabase Auth (Our Library invites them). Every table already uses "own rows", so a member cannot see your rows in another app, but they could still sign in to, say, The Brain and create rows there. So every app except Our Library accepts only your account.

- **How:** `supabase/owner-only.sql`. A small table `shared.owners` holds your user id (looked up from your email when you run it). A function `shared.is_owner()` says whether the signed-in user is in it. Every table in the schemas listed in the file's `v_schemas` gets a **restrictive** policy "owner only". A restrictive policy has to pass **as well as** the existing "own rows" policy, so access only ever gets narrower. The "own rows" policies are not touched.
- **Never locked:** `books`, `family` and `shared`. Family members keep their own rows in books, and the `family.*` functions read across members. The script refuses to lock them.
- **The email is a placeholder in the file** (`PUT-YOUR-EMAIL-HERE`, one place, marked EDIT) because this repo is public. Claude gives you the paste-ready SQL in chat with your email filled in.
- **Run it** (you, about 2 minutes): SQL Editor, **New query**, paste, **Run**. Expect "Success. No rows returned". Then open The Brain, sign in, and confirm it loads and a quick edit saves. Safe to run again.
- **When an app moves to Supabase:** add its schema to `v_schemas`, run the file again. The check at the bottom lists any app table without the lock and any view that skips it (a view needs `security_invoker = true`, as `shared.activity` has).
- **One-line check** (reads only): `select (select count(*) from shared.owners) as owners, (select count(*) from pg_policy where polname = 'owner only') as locked_tables;` Expect owners = 1 and locked_tables = the number of tables across the listed schemas (9 for The Brain alone).
- **Undo:** the block in the file's header comment drops every "owner only" policy.
- **Tested** on a local Postgres with a stand-in for Supabase's sign-in: `tests/sql/owner-only.sh` (94 checks). Owner, family member, outsider and signed-out visitor, before and after; Books and family results are identical before and after. Not tested locally: Supabase Realtime (live sync) under the new policy, so check The Brain saves and updates after running it.

## Decisions

- [x] One Supabase project (free tier) under your account: `jcm-apps`.
- [x] Pilot app: The Brain (switched over).
- [x] Second app: Books, ahead of Albums.
- [x] Shared session key for every app; The Brain moves onto it with your go-ahead.
- [x] `shared.activity` created with Books; The Brain reads it in a later pull request.
- [x] Weekly backup: the Copy Supabase → Sheet button; the GitHub Action export is deferred.
- [x] Books' claude.ai artifact: frozen read-only.
- [x] Every app except Our Library is owner-only: `supabase/owner-only.sql`; each new app's schema is added to its list as it moves (section 8).
- [ ] Run `supabase/owner-only.sql` in Supabase before the first family member signs in (trial planned about 27 Nov 2026).
- [ ] Keep-awake ping from the daily Control Room run: only if it pauses again.
- [ ] "Switch over" for Books: say it once the copy says Supabase matches your Sheet.
