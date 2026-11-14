#!/usr/bin/env bash
# Tests supabase/owner-only.sql on a throwaway local Postgres with a stand-in for Supabase's
# auth (auth.users, auth.uid() from the JWT "sub" setting, anon/authenticated roles).
# Loads the real Books SQL (01, 03, 04) and The Brain SQL (01), then acts as three people:
# Owner (O), family Member (M) and Outsider (X), before and after the lock.
#
# Run:  BOOKS_SQL=/path/to/my-book-library/supabase BRAIN_SQL=/path/to/the-brain/supabase \
#         bash tests/sql/owner-only.sh
# (the two paths default to sibling checkouts: ../my-book-library/supabase, ../the-brain/supabase)
# Needs PostgreSQL 16 binaries. Prints PASS/FAIL lines.
set -euo pipefail
cd "$(dirname "$0")/../.."
SCRIPT=$PWD/supabase/owner-only.sql
BOOKS_SQL=${BOOKS_SQL:-$PWD/../my-book-library/supabase}
BRAIN_SQL=${BRAIN_SQL:-$PWD/../the-brain/supabase}
for f in "$BOOKS_SQL/01-schema.sql" "$BOOKS_SQL/03-shared.sql" "$BOOKS_SQL/04-family.sql" "$BRAIN_SQL/01-schema.sql"; do
  [ -f "$f" ] || { echo "Missing $f (set BOOKS_SQL / BRAIN_SQL)"; exit 2; }
done
BIN=/usr/lib/postgresql/16/bin
DIR=$(mktemp -d)
chown postgres "$DIR" 2>/dev/null || true
chmod 755 "$DIR"
as_pg() { if [ "$(id -u)" = 0 ]; then su postgres -s /bin/bash -c "$*"; else bash -c "$*"; fi; }
as_pg "$BIN/initdb -D $DIR/data -A trust -U postgres >/dev/null"
as_pg "$BIN/pg_ctl -D $DIR/data -o '-k $DIR -c listen_addresses=' -l $DIR/log -w start >/dev/null"
trap 'as_pg "$BIN/pg_ctl -D $DIR/data -m immediate stop >/dev/null"; rm -rf "$DIR"' EXIT
export PGOPTIONS='-c client_min_messages=warning'
PSQL="$BIN/psql -h $DIR -U postgres -d postgres -v ON_ERROR_STOP=1 -q -X"

$PSQL <<'SQL'
create role anon nologin; create role authenticated nologin;
create schema auth;
create table auth.users (id uuid primary key, email text);
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
create publication supabase_realtime;
SQL
for f in "$BOOKS_SQL/01-schema.sql" "$BOOKS_SQL/03-shared.sql" "$BOOKS_SQL/04-family.sql" "$BRAIN_SQL/01-schema.sql"; do
  $PSQL -f "$f" >/dev/null
done

O=00000000-0000-0000-0000-00000000000a; M=00000000-0000-0000-0000-00000000000b; X=00000000-0000-0000-0000-00000000000c
$PSQL <<SQL
insert into auth.users values ('$O','owner@example.com'),('$M','member@example.com'),('$X','outsider@example.com');
select family.add_member('owner@example.com','Owner','owner');
select family.add_member('member@example.com','Member');
insert into books.books (user_id,id,title,author,status,notes,pages,current_page)
  values ('$O',1,'Shared Book','A','Reading','private note',300,120),
         ('$M',1,'Member Book','B','Reading','member note',200,10);
with t as (select (now() at time zone 'Australia/Melbourne')::date d)
insert into books.reading_log (user_id,date,pages,book_id,source)
  select '$O'::uuid, d - g, 20, 1, 'app' from t, generate_series(0,2) g
  union all select '$M', d, 15, 1, 'app' from t;
insert into family.reviews (user_id,book_id,body,stars) values ('$O',1,'Loved it',5);
-- The Brain: each person already has some rows, made before the lock exists.
insert into brain.plan (user_id,id,title) values ('$O','p1','Owner plan'),('$M','p2','Member plan'),('$X','p3','Outsider plan');
insert into brain.log (user_id,date,steps) values ('$O',current_date,1000),('$M',current_date,2000);
insert into brain.settings (user_id,key,value) values ('$O','k','owner'),('$M','k','member');
SQL

pass=0; fail=0
sql() { $PSQL -t -A -c "$1"; }
val() { # role, sub, sql -> value on the 2nd output line, or ERR if refused. Always rolled back.
  local out
  if out=$($PSQL -t -A -c "begin; set local role $1; select set_config('request.jwt.claim.sub','$2',true); $3; rollback;" 2>/dev/null); then
    printf '%s\n' "$out" | sed -n '2p'
  else echo ERR; fi
}
ok()  { echo "PASS $1"; pass=$((pass+1)); }
bad() { echo "FAIL $1 -> $2"; fail=$((fail+1)); }
check() { # name, role, sub, sql, expected
  local got; got=$(val "$2" "$3" "$4")
  if [ "$got" = "$5" ]; then ok "$1"; else bad "$1" "got [$got] want [$5]"; fi
}
refused() { # name, role, sub, sql : must be refused
  local got; got=$(val "$2" "$3" "$4")
  if [ "$got" = ERR ]; then ok "$1"; else bad "$1" "was allowed, got [$got]"; fi
}
same() { # name, a, b
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "[$2] vs [$3]"; fi
}
apply() { $PSQL -t -A -c "$(cat "$1")"; }       # runs a whole file as one batch, like the SQL Editor
variant() { sed -e "s/PUT-YOUR-EMAIL-HERE/$1/" -e "$2" "$SCRIPT" > "$3"; }
TABLES="plan routine log goals people lists notes links settings"
OWNER_ONLY="select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='%s' and p.polname='owner only' and not p.polpermissive"

battery() { # what Books and family do for each person, in one text block
  local w
  for w in "$O" "$M" "$X"; do
    echo "books.books/$w $(val authenticated $w "select count(*) from books.books")"
    echo "family.books/$w $(val authenticated $w "select coalesce(string_agg(title, ',' order by id),'-') from family.books()")"
    echo "this_month/$w $(val authenticated $w "select count(*) from family.this_month()")"
    echo "streaks/$w $(val authenticated $w "select count(*) from family.streaks()")"
    echo "reviews/$w $(val authenticated $w "select count(*) from family.reviews")"
    echo "activity/$w $(val authenticated $w "select count(*) from shared.activity")"
    echo "new-book/$w $(val authenticated $w "insert into books.books (user_id,id,title,status) values (auth.uid(),77,'New','Reading') returning title")"
    echo "recommend-to-owner/$w $(val authenticated $w "insert into family.recommendations (to_user,title) values ('$O','Dune') returning title")"
    echo "chat/$w $(val authenticated $w "insert into family.messages (family_id,body) select id,'Hi' from family.families limit 1 returning body")"
  done
  echo "signed-out/family $(val anon '' "select count(*) from family.messages")"
}
fp_policies() { sql "select coalesce(md5(string_agg(n.nspname||'.'||c.relname||'.'||p.polname||'.'||p.polpermissive::text||'.'||p.polcmd::text||'.'||p.polroles::text||'.'||coalesce(pg_get_expr(p.polqual,p.polrelid),'')||'.'||coalesce(pg_get_expr(p.polwithcheck,p.polrelid),''), ',' order by n.nspname,c.relname,p.polname)),'none') from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname in ('books','family','shared')"; }
fp_grants() { sql "select coalesce(md5(string_agg(table_schema||'.'||table_name||'.'||grantee||'.'||privilege_type, ',' order by table_schema,table_name,grantee,privilege_type)),'none') from information_schema.table_privileges where table_schema in ('books','family','shared') and not (table_schema='shared' and table_name='owners')"; }
fp_funcs() { sql "select coalesce(md5(string_agg(routine_schema||'.'||routine_name||'.'||grantee, ',' order by routine_schema,routine_name,grantee)),'none') from information_schema.routine_privileges where routine_schema in ('books','family','shared') and routine_name <> 'is_owner'"; }
fp_brain_own() { sql "select md5(string_agg(c.relname||pg_get_expr(p.polqual,p.polrelid)||pg_get_expr(p.polwithcheck,p.polrelid)||p.polpermissive::text, ',' order by c.relname)) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='brain' and p.polname='own rows'"; }

echo "== Before the lock"
check "the gap: a family member can write into The Brain today" authenticated $M "insert into brain.plan (id,title) values ('m-new','x') returning title" "x"
check "the gap: the member already sees their own Brain row" authenticated $M "select count(*) from brain.plan" "1"
before_books=$(battery); before_pol=$(fp_policies); before_gr=$(fp_grants); before_fn=$(fp_funcs); before_own=$(fp_brain_own)
before_brain_policies=$(sql "select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='brain'")

echo "== A wrong email changes nothing"
variant nobody@example.com 's/x/x/' "$DIR/wrong-email.sql"
if apply "$DIR/wrong-email.sql" >/dev/null 2>&1; then bad "unknown email is refused" "ran"; else ok "unknown email is refused"; fi
same "no owner only policy was created by the failed run" "$(sql "$(printf "$OWNER_ONLY" brain)")" "0"
same "the failed run left nothing behind, not even the owners table (all or nothing)" "$(sql "select to_regclass('shared.owners') is null")" "t"

echo "== Locked schemas that must stay open are refused"
variant owner@example.com "s/array\['brain'\]/array['brain','books']/" "$DIR/books-lock.sql"
if apply "$DIR/books-lock.sql" >/dev/null 2>&1; then bad "locking books is refused" "ran"; else ok "locking books is refused"; fi
for s in family shared; do
  variant owner@example.com "s/array\['brain'\]/array['$s']/" "$DIR/s.sql"
  if apply "$DIR/s.sql" >/dev/null 2>&1; then bad "locking $s is refused" "ran"; else ok "locking $s is refused"; fi
done
same "nothing was locked by the refused runs" "$(sql "select count(*) from pg_policy where polname='owner only'")" "0"

echo "== The lock"
variant owner@example.com 's/x/x/' "$DIR/owner-only.sql"
first=$(apply "$DIR/owner-only.sql")
same "first run succeeds and the check lists nothing open" "$first" ""
same "all nine Brain tables got a restrictive owner only policy" "$(sql "$(printf "$OWNER_ONLY" brain)")" "9"
same "exactly one owner is recorded" "$(sql "select count(*) from shared.owners")" "1"
same "the owner is the account with that email" "$(sql "select email from auth.users where id=(select user_id from shared.owners)")" "owner@example.com"
same "the existing own rows policies are untouched" "$(fp_brain_own)" "$before_own"
same "Brain has the old policies plus one new one per table" "$(sql "select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='brain'")" "$((before_brain_policies + 9))"

echo "== The owner keeps full use of The Brain"
for t in $TABLES; do
  got=$(val authenticated $O "select count(*) from brain.$t")
  case "$got" in ''|ERR|*[!0-9]*) bad "owner can read brain.$t" "got [$got]";; *) ok "owner can read brain.$t";; esac
done
check "owner sees only their own plan row" authenticated $O "select count(*) from brain.plan" "1"
check "owner still cannot see another person's Brain rows" authenticated $O "select count(*) from brain.plan where user_id in ('$M','$X')" "0"
check "owner can add a row" authenticated $O "insert into brain.plan (id,title) values ('p-new','Owner new') returning title" "Owner new"
check "owner can change their row" authenticated $O "with u as (update brain.plan set title='Edited' where id='p1' returning 1) select count(*) from u" "1"
check "owner can delete their row" authenticated $O "with d as (delete from brain.plan where id='p1' returning 1) select count(*) from d" "1"
check "owner can save a setting" authenticated $O "insert into brain.settings (key,value) values ('theme','dark') returning key" "theme"

echo "== A family member is locked out of The Brain"
for t in $TABLES; do
  check "member sees nothing in brain.$t" authenticated $M "select count(*) from brain.$t" "0"
done
check "member no longer sees even their own earlier row" authenticated $M "select count(*) from brain.plan" "0"
refused "member cannot add a Brain row" authenticated $M "insert into brain.plan (id,title) values ('m-new','x')"
refused "member cannot add a log row" authenticated $M "insert into brain.log (date,steps) values (current_date + 1, 5)"
refused "member cannot save a setting" authenticated $M "insert into brain.settings (key,value) values ('theme','x')"
check "member cannot change their earlier row" authenticated $M "with u as (update brain.plan set title='Hack' where id='p2' returning 1) select count(*) from u" "0"
check "member cannot delete their earlier row" authenticated $M "with d as (delete from brain.plan where id='p2' returning 1) select count(*) from d" "0"
check "member cannot change the owner's row" authenticated $M "with u as (update brain.plan set title='Hack' where id='p1' returning 1) select count(*) from u" "0"

echo "== An outsider and a signed-out visitor are locked out too"
check "outsider sees nothing in The Brain" authenticated $X "select count(*) from brain.plan" "0"
refused "outsider cannot add a Brain row" authenticated $X "insert into brain.plan (id,title) values ('x-new','x')"
refused "signed-out visitor cannot read The Brain" anon "" "select count(*) from brain.plan"
refused "signed-out visitor cannot write to The Brain" anon "" "insert into brain.plan (id,title) values ('a','a')"

echo "== The owner list cannot be edited from the app"
refused "owner account cannot read shared.owners from the app" authenticated $O "select count(*) from shared.owners"
refused "member cannot read shared.owners" authenticated $M "select count(*) from shared.owners"
refused "outsider cannot read shared.owners" authenticated $X "select count(*) from shared.owners"
refused "signed-out visitor cannot read shared.owners" anon "" "select count(*) from shared.owners"
refused "member cannot make themself an owner" authenticated $M "insert into shared.owners (user_id) values ('$M')"
refused "owner account cannot edit the list from the app either" authenticated $O "insert into shared.owners (user_id) values ('$M')"
refused "member cannot remove the owner" authenticated $M "delete from shared.owners"
for p in select insert update delete; do
  same "authenticated has no $p on shared.owners" "$(sql "select has_table_privilege('authenticated','shared.owners','$p')")" "f"
  same "anon has no $p on shared.owners" "$(sql "select has_table_privilege('anon','shared.owners','$p')")" "f"
done
check "is_owner() is true for the owner" authenticated $O "select shared.is_owner()" "t"
check "is_owner() is false for a member" authenticated $M "select shared.is_owner()" "f"
check "is_owner() is false for an outsider" authenticated $X "select shared.is_owner()" "f"
refused "signed-out visitors cannot call is_owner()" anon "" "select shared.is_owner()"

echo "== Books, family and shared behave exactly as before"
after_books=$(battery)
same "every Books and family result is identical for owner, member, outsider and signed-out" "$after_books" "$before_books"
same "books, family and shared policies are unchanged" "$(fp_policies)" "$before_pol"
same "books, family and shared table privileges are unchanged" "$(fp_grants)" "$before_gr"
same "books, family and shared function privileges are unchanged" "$(fp_funcs)" "$before_fn"
same "no owner only policy anywhere in books, family or shared" "$(sql "select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname in ('books','family','shared') and p.polname='owner only'")" "0"
check "member can still add their own book" authenticated $M "insert into books.books (user_id,id,title,status) values (auth.uid(),55,'Mine','Reading') returning title" "Mine"
check "member still sees the owner's shared book through family.books()" authenticated $M "select coalesce(string_agg(title, ',' order by title),'-') from family.books() where user_id='$O'" "Shared Book"
check "member still cannot read the owner's books table directly" authenticated $M "select count(*) from books.books where user_id='$O'" "0"

echo "== Running it again is safe"
apply "$DIR/owner-only.sql" >/dev/null; apply "$DIR/owner-only.sql" >/dev/null
same "still one owner after re-running" "$(sql "select count(*) from shared.owners")" "1"
same "still one owner only policy per Brain table" "$(sql "$(printf "$OWNER_ONLY" brain)")" "9"
same "Brain policy count is unchanged after re-running" "$(sql "select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='brain'")" "$((before_brain_policies + 9))"
same "own rows policies still untouched after re-running" "$(fp_brain_own)" "$before_own"

echo "== A new table or a new app is caught"
$PSQL <<SQL
create table brain.extra (row_id bigint generated always as identity primary key, user_id uuid not null default auth.uid(), note text);
alter table brain.extra enable row level security;
create policy "own rows" on brain.extra for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
grant select, insert, update, delete on brain.extra to authenticated;
grant usage, select on all sequences in schema brain to authenticated;
create schema albums;
create table albums.items (row_id bigint generated always as identity primary key, user_id uuid not null default auth.uid(), title text);
alter table albums.items enable row level security;
create policy "own rows" on albums.items for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
grant usage on schema albums to authenticated;
grant select, insert, update, delete on albums.items to authenticated;
grant usage, select on all sequences in schema albums to authenticated;
create view albums.v_bad as select title from albums.items;
create view albums.v_ok with (security_invoker = true) as select title from albums.items;
SQL
check "before re-running, a table made after the lock is open to a member (why the check exists)" authenticated $M "insert into brain.extra (note) values ('x') returning note" "x"
out=$(apply "$DIR/owner-only.sql")
want=$'albums|items|table without the owner only policy\nalbums|v_bad|view that skips the lock (needs security_invoker = true)'
same "the check lists an unlocked app schema's table and a view that skips the lock" "$out" "$want"
same "a new table in a listed schema is locked by simply running it again" "$(sql "select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid where c.relname='extra' and p.polname='owner only'")" "1"
refused "member cannot write to the new Brain table" authenticated $M "insert into brain.extra (note) values ('x')"
check "owner can write to the new Brain table" authenticated $O "insert into brain.extra (note) values ('x') returning note" "x"
variant owner@example.com "s/array\['brain'\]/array['brain','albums']/" "$DIR/with-albums.sql"
out=$(apply "$DIR/with-albums.sql")
same "adding albums to the list locks its table; only the leaky view is left" "$out" "albums|v_bad|view that skips the lock (needs security_invoker = true)"
$PSQL -c "alter view albums.v_bad set (security_invoker = true)"
same "the check is empty once the view runs as the signed-in user" "$(apply "$DIR/with-albums.sql")" ""
refused "member cannot write to the albums table" authenticated $M "insert into albums.items (title) values ('x')"
check "owner can write to the albums table" authenticated $O "insert into albums.items (title) values ('Violator') returning title" "Violator"
check "own rows still apply: owner sees only their own album rows" authenticated $O "select count(*) from albums.items" "0"

echo "== Undo works, and the lock comes back"
$PSQL -c "do \$\$ declare r record; begin for r in select schemaname, tablename from pg_policies where policyname = 'owner only' loop execute format('drop policy \"owner only\" on %I.%I', r.schemaname, r.tablename); end loop; end \$\$"
same "undo removed every owner only policy" "$(sql "select count(*) from pg_policy where polname='owner only'")" "0"
check "after undo the member can write again (the old behaviour)" authenticated $M "insert into brain.plan (id,title) values ('m-new','x') returning title" "x"
apply "$DIR/with-albums.sql" >/dev/null
refused "after running it again the member is locked out" authenticated $M "insert into brain.plan (id,title) values ('m-new','x')"

echo "$pass PASS, $fail FAIL"
[ "$fail" = 0 ]
