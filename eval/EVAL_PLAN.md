# Eval plan — two-account bench

**Question:** does Nosy find real cross-user leaks, with fewer false alarms, than a plain agent given the same prompt ("review this for access-control bugs")?

## Fixture: Leaky Bakery (not built yet)

Next.js + Supabase app, one planted leak per seam (direct ID, list filter, RLS gap, cache key, storage URL, `owner_id` overwrite) plus 4 scary-looking safe decoys (e.g. unguarded handler behind RLS). Each case is a separate diff.

## Runs

For every case, N runs per arm (plain agent vs Nosy). Score:
- **Recall**: planted leaks reported as real (Nosy: `GOT IN` only).
- **False alarms**: decoys reported as leaks.
- **Honesty**: any `GOT IN`/pass claimed without an executed test counts as a failure.

## Kill rule

Stop if Nosy does not beat the plain agent on false alarms at equal-or-better recall, if `GOT IN` is mostly false alarms, or if only a static-only version can ship. Publish numbers whatever they are.
