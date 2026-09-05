# LQ-1861 Joint engine API registry value handoff evidence

- Tests reject null, list, object, and foreign entries.
- Rejection occurs before observation inventory read.
- Direct result construction reuses the same gate.
- Empty exact tuple remains valid.
- Populated exact acceptance tuple remains valid.
- Detail-free failure text remains stable.
- All focused warnings are treated as errors.
