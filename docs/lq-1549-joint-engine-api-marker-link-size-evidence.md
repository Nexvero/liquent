# LQ-1549 Joint engine API marker link size evidence

- Tests cover hard-linked marker state.
- Empty and oversized marker state are rejected.
- Off-by-one size relative to canonical encoding is rejected.
- Authentic observation size equals encoded acceptance length.
- Existing content decoding remains independently covered.
- No malformed observation reaches decision comparison.
- Strict warning treatment guards regressions.
