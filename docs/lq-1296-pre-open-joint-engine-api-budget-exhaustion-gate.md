# LQ-1296 Pre-open joint engine API budget exhaustion gate

- The common ordered loader evaluates remaining bytes at loop entry.
- A nonpositive remainder raises before the child reader call.
- Positive remainder is narrowed against the canonical per-file maximum.
- Completed source bytes are added only after stable child validation.
- No new file API, alternate loader, or configuration surface is added.
- All three public layout loaders inherit the gate automatically.
- Existing directory revalidation still follows complete successful capture.
