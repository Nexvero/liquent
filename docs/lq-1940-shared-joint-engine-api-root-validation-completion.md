# LQ-1940 Shared joint engine API root validation completion

- One helper invokes final root validator.
- It accepts only normal none completion.
- Raw validator return never reaches operation caller.
- Read-only and mutation-aware paths share the helper.
- Existing validator remains root-state authority.
- No fallback success interpretation is available.
- No new port or persistence model is introduced.
