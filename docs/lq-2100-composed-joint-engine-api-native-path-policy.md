# LQ-2100 Composed joint engine API native Path policy

- Parser handoff and direct APIs share one type fact.
- Exact type precedes lexical root checks.
- Lexical checks precede persisted authority checks.
- Root resolution remains system-of-record authority.
- CLI dispatch grants no path authority.
- No normalization fallback exists.
- No persistence behavior changes.
