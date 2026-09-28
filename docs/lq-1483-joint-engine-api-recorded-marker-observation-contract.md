# LQ-1483 Joint engine API recorded marker observation contract

- Successful record returns the marker generation it durably created.
- Observation combines requested acceptance and descriptor identity.
- Identity comes from the still-open written marker descriptor.
- Return occurs only after file sync, verification, and directory sync.
- Failed or uncertain record does not fabricate an observation.
- The observation grants no authority beyond durable write evidence.
- Existing callers may safely ignore the additive return value.
