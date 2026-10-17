# Harness recipes

Load this when writing the step-2 tests. Every recipe has the same shape as SKILL.md: two users, a canary, controls, then attacks through the real entry point. Adapt the names to the repo; these are sketches, not drop-ins.

## Supabase / Postgres RLS (pgTAP)

Put the file at `supabase/tests/database/nosy_<table>.test.sql` and run it with `supabase test db`. This needs the local stack (`supabase start`); ask before starting it.

```sql
begin;
create extension if not exists pgtap with schema extensions;
select plan(6);

insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111', 'alice@nosy.test'),
  ('22222222-2222-2222-2222-222222222222', 'nosy@nosy.test');

-- seed as the table owner (bypasses RLS on purpose)
insert into public.videos (user_id, title) values
  ('11111111-1111-1111-1111-111111111111', 'nosy-canary-7f3a9c'),
  ('22222222-2222-2222-2222-222222222222', 'nosy-own-row');
select isnt_empty($$ select 1 from public.videos where title = 'nosy-canary-7f3a9c' $$, 'control: canary seeded');

-- become nosy: the app role, plus the claims the policies read
set local role authenticated;
set local request.jwt.claims to '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}';
select is(current_user::text, 'authenticated', 'control: running as app role, not table owner');
select isnt_empty($$ select 1 from public.videos where title = 'nosy-own-row' $$, 'control: nosy sees own row');

select is_empty($$ select 1 from public.videos where title = 'nosy-canary-7f3a9c' $$, 'read: nosy cannot see alice''s row');
select throws_ok($$ insert into public.videos (user_id, title)
                    values ('11111111-1111-1111-1111-111111111111', 'planted') $$,
                 '42501', null, 'create: nosy cannot plant rows owned by alice');

update public.videos set title = 'pwned' where user_id = '11111111-1111-1111-1111-111111111111';
delete from public.videos where user_id = '11111111-1111-1111-1111-111111111111';
reset role;  -- back to owner to inspect the damage
select is((select count(*)::int from public.videos where title = 'nosy-canary-7f3a9c'), 1,
          'write: alice''s row neither changed nor deleted');

select * from finish();
rollback;
```

- **Set the claims your policies read.** Policies built on `auth.uid()` read `sub` as a uuid. Clerk or other third-party auth usually means `auth.jwt()->>'sub'` holding a text id like `user_2abc`, so match that format, and add `org_id` and `role` claims if the policies use them.
- **If the write check fails, find out which write got in.** Split the update and the delete into separate checks, switching roles between them, so the ledger can name the operation.
- **Views.** Run the same read attack against the view. A view without `security_invoker = true` runs as its owner, which bypasses RLS.
- **Storage.** Use the same pattern on `storage.objects` (`bucket_id`, `name`, `owner`). With no local storage, mark it `NOT CHECKED`.
- **A pgTAP pass clears the policy, not the app.** It only clears an app path if that path uses a client that RLS applies to. Cite where that client is created.

## HTTP routes (Next.js route handlers, Express, Hono, …)

Use the repo's runner (vitest, jest, `node:test`, supertest) and its local test DB. If there is a test login helper, use it. Otherwise mock **only** the function that says who the caller is. In Jest, a mocked variable must start with `mock`.

```ts
// tests/nosy/videos.test.ts (sketch)
let mockUser = 'nosy'
vi.mock('@/lib/auth', () => ({ getUserId: async () => mockUser }))  // identity only, never the DB

const CANARY = `nosy-canary-${crypto.randomUUID().slice(0, 8)}`
let aliceVideo: string, nosyVideo: string

beforeAll(async () => {
  mockUser = 'alice'; aliceVideo = (await call('POST', '/api/videos', { title: CANARY })).id
  mockUser = 'nosy';  nosyVideo  = (await call('POST', '/api/videos', { title: 'nosy-own' })).id
})

test('control: nosy reads own video', async () => {
  mockUser = 'nosy'
  expect(JSON.stringify(await call('GET', `/api/videos/${nosyVideo}`))).toContain('nosy-own')
})

test('read: alice\'s canary never reaches nosy', async () => {
  mockUser = 'nosy'
  expect(JSON.stringify(await call('GET', `/api/videos/${aliceVideo}`))).not.toContain(CANARY)
  expect(JSON.stringify(await call('GET', '/api/videos'))).not.toContain(CANARY)  // list
})

test('update: alice\'s row unchanged', async () => {
  mockUser = 'nosy';  await call('PATCH', `/api/videos/${aliceVideo}`, { title: 'pwned' })
  mockUser = 'alice'; expect(JSON.stringify(await call('GET', `/api/videos/${aliceVideo}`))).toContain(CANARY)
})
```

- `call()` is a tiny helper: invoke the route handler directly, or go through supertest. It returns the parsed body whatever the status is. The canary decides, not the status code.
- Create alice's data through the real create path when you can. That exercises the owner assignment too.
- Also try mass assignment: `nosy` PATCHes its own row with `{ user_id: <alice> }`, then check who owns it.

## Service functions / ORM

If handlers are thin wrappers, attack the service function directly with a context user and a real local DB (an SQLite file, or a local Postgres container if one is already running). This is the fallback when the HTTP layer is hard to drive. Note in the ledger that the route wrapper wasn't exercised.

## Before you trust the run

- The runner reported the file and the expected number of tests. "No tests found" is `NOT CHECKED`, not green.
- The DB the test touched is local. Re-check it if the test reads `.env`.
- A failure is a canary or row-unchanged assertion, not a crash. A crash is a harness problem.
