# LQ-1489 Joint engine API post-record generation evidence

- Tests observe equality between record and final marker observations.
- They replace the marker with the same canonical bytes after record.
- The replacement preserves owner-private mode but changes inode.
- One-shot acceptance rejects that replacement generation.
- Expected registry identity reaches the final observation.
- Existing marker-value readback remains regression-covered.
- Strict warning treatment guards compatibility regressions.
