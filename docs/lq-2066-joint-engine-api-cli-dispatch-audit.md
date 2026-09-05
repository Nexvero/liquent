# LQ-2066 Joint engine API CLI dispatch audit

- Main no longer owns inline routing branches.
- Dispatcher owns all operation selection.
- Caller mode cannot supply an Audit boolean.
- Result payload cannot imply success.
- Parser and dispatcher remain separate.
- Direct request preflight remains authoritative.
- No durable layout changes.
