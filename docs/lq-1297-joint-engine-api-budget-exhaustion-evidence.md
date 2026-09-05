# LQ-1297 Joint engine API budget exhaustion evidence

- Tests set the aggregate ceiling to exactly the first source size.
- The first canonical source opens and validates successfully.
- The next canonical source is never passed to the child reader.
- Zero aggregate allowance proves that no source reader is invoked at all.
- Policy-, image-, and run-bound layouts are each covered.
- Observation wraps the real loader rather than replacing read behavior.
- Architecture guardrails remain part of focused evidence.
