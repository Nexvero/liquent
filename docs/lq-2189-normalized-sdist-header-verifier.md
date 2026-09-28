# LQ-2189 Normalized sdist header verifier

- SOURCE_DATE_EPOCH is bounded to the unsigned Gzip timestamp field.
- The Gzip magic and compression method must be exact.
- Optional Gzip header flags are absent.
- Header time equals the same epoch used for every tar member.
- Numeric owners are zero and owner names are empty.
- Normalized PAX output contains only canonical long-path records.
- Any mismatch rejects the temporary output before replacement.
