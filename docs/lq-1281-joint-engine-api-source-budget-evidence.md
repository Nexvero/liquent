# LQ-1281 Joint engine API source budget evidence

- Tests pin the aggregate ceiling to exactly 64 MiB.
- Exact cumulative source size is accepted for every supported layout.
- One byte below that observed size rejects every supported layout.
- Evidence distinguishes actual bytes from summed per-file maxima.
- Mismatched internal name and limit collections fail closed.
- Existing stable-file and stable-directory evidence remains in scope.
- Focused verification covers this evidence under strict warnings.
