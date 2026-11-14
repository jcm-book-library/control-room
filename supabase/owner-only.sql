-- Owner only: lock the apps that are just for you, so a family member who signs in to
-- Our Library still cannot read or write anything in The Brain (or any other private app).
--
-- HOW TO RUN (about 2 minutes), in Supabase:
--   1. Change PUT-YOUR-EMAIL-HERE below (one place, marked EDIT) to the email you sign in with.
--      Not sure which? Run this first:  select id, email from auth.users;
--   2. SQL Editor > New query > paste all of this > Run.
--      If Supabase shows a warning about "destructive" changes, it is the "drop policy if
--      exists" lines, which only replace the lock if it is already there. Run it anyway.
--   3. Expect: "Success. No rows returned". Any rows listed are tables still open (see the
--      check at the very bottom).
--   4. Open The Brain, sign in, and confirm it loads and a quick edit saves.
-- Safe to run again, any time. If it fails, no policy has been changed.
--
-- WHAT IT DOES
--   * shared.owners holds your user id. Nobody can read or edit it through the app.
--   * shared.is_owner() says whether the signed-in user is in that list. (This is you, the
--     account owner. It is not the "owner" role inside a family.)
--   * Every table in the schemas listed in the second block gets a RESTRICTIVE policy
--     "owner only". A restrictive policy must pass AND the existing "own rows" policy must
--     pass, so access only ever gets narrower. The "own rows" policies are not touched.
--   * Signed-out visitors already get nothing (no grants), and still do.
--   * Books, family and shared are never locked here: family members keep their own rows in
--     books, and the family.* functions read across members.
--
-- WHEN ANOTHER APP MOVES TO SUPABASE (albums, tv, games, films, pantry ...)
--   Add its schema name to v_schemas in the second block, then run this file again.
--   The check at the bottom lists any app schema you forgot.
--
-- TO UNDO (rare). Run this on its own; The Brain is then open to any signed-in user again:
--   do $$ declare r record; begin
--     for r in select schemaname, tablename from pg_policies where policyname = 'owner only' loop
--       execute format('drop policy "owner only" on %I.%I', r.schemaname, r.tablename);
--     end loop; end $$;

create schema if not exists shared;

-- ---------- 1. who the owner is ----------

create table if not exists shared.owners (
  user_id uuid primary key references auth.users on delete cascade
);

-- Row Level Security on and no policies: nobody but the database owner (the SQL Editor) can
-- read or change this list. The revoke removes any default grant to the app's roles.
alter table shared.owners enable row level security;
revoke all on shared.owners from public, anon, authenticated;

do $$
declare
  v_email constant text := 'PUT-YOUR-EMAIL-HERE';   -- EDIT: the email you sign in to your apps with
begin
  if not exists (select 1 from auth.users where lower(email) = lower(v_email)) then
    raise exception 'No account with the email "%". Edit the email near the top of this script and run it again. No policy was changed.', v_email;
  end if;
  insert into shared.owners (user_id)
  select id from auth.users where lower(email) = lower(v_email)
  on conflict do nothing;
end $$;

create or replace function shared.is_owner() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from shared.owners where user_id = (select auth.uid()))
$$;

revoke all on function shared.is_owner() from public, anon;
grant usage on schema shared to authenticated;
grant execute on function shared.is_owner() to authenticated;

-- ---------- 2. lock the private apps ----------

do $$
declare
  v_schemas constant text[] := array['brain'];   -- ADD an app's schema here when it moves
  never_lock constant text[] := array['books', 'family', 'shared', 'public', 'auth', 'storage',
    'realtime', 'vault', 'extensions', 'graphql', 'graphql_public', 'information_schema'];
  s text;
  t text;
  n int := 0;
begin
  foreach s in array v_schemas loop
    if s = any (never_lock) or s like 'pg\_%' then
      raise exception 'Refusing to lock schema "%": it has to stay open to family members or to Supabase itself. No policy was changed.', s;
    end if;
  end loop;

  foreach s in array v_schemas loop
    if to_regnamespace(quote_ident(s)) is null then
      raise notice 'Schema % does not exist yet, skipped', s;
      continue;
    end if;
    for t in
      select c.relname from pg_class c join pg_namespace ns on ns.oid = c.relnamespace
      where ns.nspname = s and c.relkind in ('r', 'p') order by 1
    loop
      execute format('alter table %I.%I enable row level security', s, t);
      execute format('drop policy if exists "owner only" on %I.%I', s, t);
      execute format('create policy "owner only" on %I.%I as restrictive for all to authenticated
                      using ((select shared.is_owner())) with check ((select shared.is_owner()))', s, t);
      n := n + 1;
    end loop;
  end loop;
  raise notice 'owner only policy set on % tables', n;
end $$;

notify pgrst, 'reload schema';

-- ---------- Check: expect "Success. No rows returned" ----------
-- Lists anything in an app schema that is not locked to the owner: a table without the
-- "owner only" policy, or a view that does not run as the signed-in user (a view that skips
-- that would bypass the lock). Books, family and shared are meant to stay open and are skipped.
select ns.nspname as "schema", c.relname as "name",
       'table without the owner only policy' as problem
from pg_class c join pg_namespace ns on ns.oid = c.relnamespace
where c.relkind in ('r', 'p')
  and ns.nspname not in ('books', 'family', 'shared', 'public', 'auth', 'storage', 'realtime', 'vault',
                         'extensions', 'graphql', 'graphql_public', 'information_schema',
                         'supabase_functions', 'supabase_migrations', 'net', 'cron', 'pgbouncer')
  and ns.nspname not like 'pg\_%'
  and not exists (select 1 from pg_policy p
                  where p.polrelid = c.oid and p.polname = 'owner only' and not p.polpermissive)
union all
select ns.nspname, c.relname, 'view that skips the lock (needs security_invoker = true)'
from pg_class c join pg_namespace ns on ns.oid = c.relnamespace
where c.relkind in ('v', 'm')
  and ns.nspname not in ('books', 'family', 'shared', 'public', 'auth', 'storage', 'realtime', 'vault',
                         'extensions', 'graphql', 'graphql_public', 'information_schema',
                         'supabase_functions', 'supabase_migrations', 'net', 'cron', 'pgbouncer')
  and ns.nspname not like 'pg\_%'
  and not coalesce(c.reloptions @> array['security_invoker=true'], false)
order by 1, 2;
