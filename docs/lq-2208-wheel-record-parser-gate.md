# LQ-2208 Wheel RECORD parser gate

- RECORD is strict UTF-8 CSV with LF termination and no carriage returns.
- Every row contains exactly three fields.
- Row names equal ZIP member names in the same sequence.
- URL-safe SHA-256 values omit base64 padding exactly.
- Sizes use the canonical decimal spelling of bytes actually read.
- CSV, encoding, field-count, and coverage errors fail closed.
- Existing member bounds limit RECORD parsing and payload rereads.
