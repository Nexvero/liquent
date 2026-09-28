# LQ-1399 Joint engine API acceptance post-write contract

- A created acceptance marker is verified before successful materialization.
- Verification uses the same descriptor that exclusively created the file.
- Stored bytes must exactly equal the canonical encoded acceptance value.
- Owner, private mode, single link, exact size, and regular type are required.
- File metadata must remain stable throughout descriptor readback.
- A failed readback yields no trusted or observable success result.
- Callers cannot disable or replace post-write verification.
