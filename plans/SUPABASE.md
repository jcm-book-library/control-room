# Plan: moving the apps to Supabase

Status: **The Brain is the pilot and is built; its data copy is not yet verified.** Updated 2 Nov 2026 (first written 19 Oct 2026). Every other app is still on its Google Sheet.

## Next steps for The Brain (in order)

The project is **paused**, so start there.

1. **Restore the project** (Supabase dashboard, 2 minutes).
   1. Open https://supabase.com/dashboard and click **jcm-apps**.
   2. Click the green **Restore project** button on the paused banner, then wait a few minutes until the project opens.
   3. If there is no restore button and the dashboard says the project can't be restored, tell Claude before doing anything else. The Sheet still has everything.
2. **See what's in it.** SQL Editor, **+ New query**, paste `supabase/02-check.sql` from the-brain repo, **Run**. It lists each table with its row count and whether row protection is on.
   - Nine tables, protection on, rows in them: carry on.
   - Tables there but no rows: the copy was never done. Step 4 does it.
   - Error saying the `brain` schema doesn't exist: run steps 1 to 3 of `supabase/SETUP.md` first.
3. **Put the sign-in code in the email.** Authentication, **Email Templates**, **Magic link**. Under the link add `<p>Your sign-in code: <b>{{ .Token }}</b></p>` and **Save**. (This is what makes phone sign-in work.)
4. **Laptop:** open The Brain, **Settings**, type your email, **Email me a sign-in link**, then type the code into the box. Click **Check Sheet and Supabase match**.
   - If they differ and the Sheet is the up-to-date one: **Copy Sheet to Supabase**, then **Check** again. It should say they match on every tab.
5. **Phone:** **Settings**, email, code, choose **Supabase** under *Where your data lives*, **Save & connect**.
6. **Tell Claude "switch over."** Supabase becomes the default on every device. The Sheet is kept as an archive and never written again without your go-ahead.

Done once switch-over has happened and a week has passed with nothing missing: The Brain is finished, and the next app can start.

## In short

- **One Supabase project** for every app (`jcm-apps`, Sydney), one schema (folder of tables) per app, and sign-in so only you can read or write.
- **The Brain went first** (your choice), not TV Tracker as first planned. It is where the pattern was built and tested.
- **Google Sheets stay** as a read-only archive, plus a weekly export back to a backup sheet so you can still browse your data in Sheets.
- **The Brain then reads one shared "activity" view** instead of reaching into five different sheets.
- **Keep it awake.** Free projects pause after about a week without use, and the pilot did exactly that because the Sheet was still the default. Switching The Brain over fixes it (you use it daily); section 4 has a backup plan.

## 1. One project for all apps

| Piece | Choice | Why |
|---|---|---|
| Project | One: `jcm-apps`, Sydney region (created) | One sign-in, one bill, and The Brain can read across apps |
| Tables | One schema per app: `brain` (built), then `tv`, `books`, `albums`, `games`, `films`, `pantry` … | Same "stay in your lane" rule as the sheet tabs today |
| Shared | Schema `shared` holding the `activity` view (section 6) | The only place apps meet |
| Sign-in | Supabase Auth: email link or code today; Google sign-in can be added later | Works now without Google Cloud steps |
| Security | Row Level Security on every table: only your user id can read or write. Sign-ups switched off after your first sign-in | The public key in the app code is then safe in a public repo |
| Plan | Free tier | Caveat: pauses after about a week without use (section 4) |

The house rules carry over: permanent ids, dates as real dates, no bulk rewrites from the app, a backup before any change of shape. Never put the `service_role` key or the database password in a chat.

## 2. What The Brain proved (the recipe for every other app)

Each app moves the same way. **You** do the Supabase clicks; **Claude** does the code and tests.

1. **Schema.** Claude writes one numbered SQL file (`01-schema.sql`): tables matching the Sheet tabs column for column, plus `row_id`, `user_id`, `updated_at`; Row Level Security on; no access for signed-out visitors. **You** paste it once into the SQL Editor.
2. **Expose the schema.** **You** add the new schema to *Exposed schemas* in the Data API settings. Supabase doesn't do this automatically.
3. **Supabase mode beside the Sheets mode.** Claude adds it behind the app's data functions, so the screens never talk to either directly. Each device picks its source in Settings.
4. **Copy and check.** One button copies Sheet to Supabase, then reads Supabase back and compares every row. It refuses if the Sheet has duplicate ids.
5. **Run side by side.** A second button copies Supabase back to the Sheet: it shows what will change, makes a dated hidden backup of each tab first, writes only the cells that differ, then reads the Sheet back to check.
6. **Check button.** Read-only: lists every tab with its row count in each place and says what differs. Use it whenever you're unsure.
7. **Tests.** Three headless test suites run before every push: the Sheets mode, the Supabase mode, and the copy-back. Each new app gets the same three.
8. **Switch over.** Supabase becomes the default on every device. The Sheet is kept as an archive.

Lessons from the pilot:
- **Phone home-screen apps** keep separate storage from the browser, so an emailed *link* signs in the wrong place. A typed *code* works. Every app should offer the code.
- **A pilot that isn't the default doesn't get used**, so the project paused. Move quickly from "side by side" to "switched over".
- **Tab headers live in row 1 of every Sheet tab**, so "Moved to Supabase" notes can't go in A1. Use a separate note tab, and only with your go-ahead.

## 3. Sign in once for every app

All the apps are on `jcm-book-library.github.io`, so they share browser storage (the Google token already works this way). When a second app moves, every app should use **one shared session key**, so signing in on a device covers all of them. Until then The Brain keeps its own key (`brain-sb-session`).

## 4. Keeping it awake

- Once The Brain is switched over, daily use keeps the project awake.
- **Backup plan:** the daily Control Room run makes one harmless request to the project so it never idles for a week. It only needs the public key, and it reads nothing private. Add it only if the project pauses again; it is a small change to the Control Room workflow, through a pull request.
- If it pauses anyway, **Restore project** brings it back (steps at the top). The dashboard shows how long a paused project can be restored, so don't leave it for months.

## 5. What happens to the Google Sheets

- **Nothing is deleted.** Each tab is frozen at its switch-over date and kept as an archive.
- **Weekly export:** a GitHub Action copies each Supabase table to a backup Google Sheet (new dated tab each time, last 8 kept). This is your "open it in Sheets" view and an off-Supabase backup.
- **claude.ai artifacts** use the Google Sheets connector today. During the pilot they keep reading the sheet; after switch-over they read the backup sheet (read-only) or a Supabase connector if you add one.
- Apps not yet moved keep working exactly as now.

## 6. How The Brain reads other apps

A view `shared.activity` stacks every app's log in one agreed layout:

`date | app | item_id | title | amount | unit | logged_at | source | note`

| App | amount / unit |
|---|---|
| Books | pages |
| TV | episodes |
| Albums | plays |
| Games | minutes |
| Films | watches |

The Brain reads this view only (never writes to other apps). Its Pages, Episodes and similar figures fill themselves from the view, and a number you typed yourself is never overwritten. Each app joins the view as it moves, so The Brain gains books first if Books moves before others. Today pages are typed into The Brain's daily log by hand.

## 7. Order

1. **The Brain**: built; finish with the steps at the top.
2. **Albums**: smallest, so the second app proves the recipe with little at stake.
3. **Books**: largest and most used, so it goes once the recipe is proven. It is also the first feed into `shared.activity`.
4. **TV Tracker**: cleanest id column and a 53-check smoke test, so a low-risk move.
5. **Games and Films**, then the rest.

## Decisions for you

- [x] One Supabase project (free tier) under your account: **done, `jcm-apps`.**
- [x] Pilot app: **The Brain** (TV Tracker is now fourth in line).
- [ ] Weekly export back to a backup Google Sheet: yes or no? (Recommended: yes. Cheap insurance, and you can still browse your data in Sheets.)
- [ ] Keep-awake ping from the daily Control Room run: now, or only if it pauses again?
- [ ] OK with the order in section 7?
- [ ] "Switch over" for The Brain: say it once step 4 above says Supabase matches your Sheet.
