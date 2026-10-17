# Example 3 — BLOCKED (so it's not just alarms)

Diff adds a `projects` table and a `GET /api/projects/:id` handler that queries by id only, with the user-scoped client.

`supabase/migrations/0004_rls.sql`:

```sql
8  alter table projects enable row level security;
9  create policy projects_owner on projects
10   using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

Nosy's pgTAP test, run with `supabase test db`: as `nosy`, `select`, `update` and `delete` on alice's row return 0 rows affected; an insert with `user_id = alice` is rejected.

```
nosy · 4 paths tried on this diff
BLOCKED      4 paths: read, update, delete, owner_id overwrite
             RLS "projects_owner" (supabase/migrations/0004_rls.sql:9-10), pgTAP green
```

The handler looks unguarded, but the invariant is in the database, so nothing is reported against it.
