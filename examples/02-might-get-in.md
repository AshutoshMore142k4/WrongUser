# Example 2 — MIGHT GET IN (no running falsifier)

Diff changes a cache helper: `cache.get(`render:${req.url}`)` wraps a handler that returns the caller's renders. The key has no user id.

The repo has no Redis emulator and no test config, and installing one needs approval that was not given.

```
wronguser · 1 path tried on this diff
MIGHT GET IN  GET /api/renders — cache key omits user
              src/lib/cache.ts:14 key = `render:${req.url}` (no user/tenant)
              src/app/api/renders/route.ts:8 returns per-user rows through that cache
              not run: no Redis emulator available; ask to install one to upgrade this to GOT IN or BLOCKED
```

Never labelled `GOT IN`: nothing was executed.
