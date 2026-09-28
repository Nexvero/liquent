# LQ-1843 Joint engine API accept handoff type contract

- Verify-and-accept returns one exact marker observation.
- Null and foreign return forms are rejected.
- An acceptance value alone is not sufficient evidence.
- Type validation precedes post-mutation inventory reads.
- No coercion or duck typing grants trust.
- Failure remains detail-free.
- Public accept-once behavior remains unchanged.
