# Leak catalog

For each: what to look for, the attack as `nosy`, and what counts as an invariant for `BLOCKED`.

| Leak | Look for | Attack | Invariant that blocks it |
|---|---|---|---|
| Direct ID access | `findById(params.id)` / `.eq('id', id)` with no owner filter | `nosy` GETs alice's resource id → expect 404/403 | owner predicate in the query, or RLS policy on the table |
| Missing list/search filter | list/search handlers that query without `user_id` | `nosy` lists/searches → alice's rows must be absent | owner filter in the query, or RLS |
| GraphQL resolvers | resolvers (queries **and** mutations) that fetch by id without context user | query and mutate alice's id as `nosy` | per-resolver or directive-level ownership check |
| RLS gaps | table without `enable row level security`; `using (true)`; views (run as owner, bypass RLS unless `security_invoker`); service-role key reachable from the client | pgTAP as `nosy` JWT: select/update/delete alice's row; query via the view | policy `using (auth.uid() = user_id)` **and** `with check` on write |
| Cache key omits user | `cache.get(key)` where key has no user/tenant | alice warms cache, `nosy` requests same URL | user/tenant in the cache key |
| RAG retrieval without ACL | vector search with no metadata/namespace filter | `nosy` asks a question only alice's doc answers | ACL filter or per-tenant namespace in the retrieval call |
| Storage URLs | public buckets, guessable paths, long-lived signed URLs | `nosy` fetches alice's object path unauthenticated and as `nosy` | private bucket + storage policy, or short-lived signed URL minted after an ownership check |
| Wrong principal in jobs | background job using service role/admin on user-supplied ids | enqueue job as `nosy` with alice's resource id | ownership check before enqueue or inside the job |
| `owner_id` overwrite | update/insert spreading request body into the row | `nosy` PATCHes own row with `owner_id: alice` (or alice's row with own id) | allow-listed fields; `with check` forbidding owner change |

Read **and** write: an enforced read with an unguarded update is still `GOT IN`.
