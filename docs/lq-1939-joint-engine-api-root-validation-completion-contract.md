# LQ-1939 Joint engine API root validation completion contract

- Final root validation completes only with exact none result.
- Any foreign return value fails closed.
- Validation exceptions remain authoritative failures.
- Completion check applies to success and failure paths.
- Existing validator arguments remain unchanged.
- Failure remains detail-free.
- Public command behavior remains unchanged.
