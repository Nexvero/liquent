# LQ-1609 Joint engine API marker preservation evidence

- Tests establish one canonical pre-existing marker.
- Inner acceptance creates the expected new marker.
- Test replaces the old marker with identical canonical bytes.
- Changed generation causes final delta rejection.
- Normal empty-to-single-marker delta remains successful.
- Existing expected-delta tests remain green.
- Strict warning treatment guards regressions.
