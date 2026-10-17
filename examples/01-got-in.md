# Example 1 — GOT IN (direct ID access)

Diff adds `app/api/videos/[id]/route.ts`:

```ts
export async function GET(req, { params }) {
  const { data } = await supabaseAdmin.from('videos').select('*').eq('id', params.id).single()
  return Response.json(data)
}
```

`supabaseAdmin` uses the service role, so RLS never applies; no owner filter in the query.

Nosy writes `tests/nosy/videos.test.ts`: alice creates a video titled with a canary (`nosy-canary-7f3a9c`), `nosy` creates its own. Control: `nosy` can `GET` its own video. Attack: `nosy` calls `GET /api/videos/<alice's id>` and asserts the canary is not in the response.

```
nosy · 1 path tried on this diff
GOT IN       GET /api/videos/:id → nosy read alice's video
             tests/nosy/videos.test.ts › "read: canary never reaches nosy" FAILED
             response contained "nosy-canary-7f3a9c" (control: nosy reads own video, passed)
```

Proposed fix (asked before editing): use the user-scoped client, or add `.eq('user_id', session.userId)`. Re-run: test green.
