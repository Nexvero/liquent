# LQ-2510 Second intermediate listing gate

- The first child pass is followed by a second descriptor-relative listing.
- Its exact set must equal the names observed at the start of verification.
- Addition, removal, or renaming during inspection fails closed.
- No callback or receipt parsing occurs between the two observations.
- The held workspace descriptor remains the namespace anchor throughout.
- Listing stability is necessary but does not replace identity continuity.
