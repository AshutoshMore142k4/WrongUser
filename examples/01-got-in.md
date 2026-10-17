# Example 1 — GOT IN (direct ID access)

Diff adds `app/api/videos/[id]/route.ts`:

```ts
export async function GET(req, { params }) {
  const { data } = await supabaseAdmin.from('videos').select('*').eq('id', params.id).single()
  return Response.json(data)
}
```

`supabaseAdmin` uses the service role, so RLS never applies; no owner filter in the query.

WrongUser writes `tests/wronguser/videos.test.ts`: alice creates a video titled with a canary (`wronguser-canary-7f3a9c`), `wronguser` creates its own. Control: `wronguser` can `GET` its own video. Attack: `wronguser` calls `GET /api/videos/<alice's id>` and asserts the canary is not in the response.

```
wronguser · 1 path tried on this diff
GOT IN       GET /api/videos/:id → wronguser read alice's video
             tests/wronguser/videos.test.ts › "read: canary never reaches wronguser" FAILED
             response contained "wronguser-canary-7f3a9c" (control: wronguser reads own video, passed)
```

Proposed fix (asked before editing): use the user-scoped client, or add `.eq('user_id', session.userId)`. Re-run: test green.
