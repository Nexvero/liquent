# LQ-1544 Closed joint engine API marker observation value

- Immutable construction validates shape and file semantics.
- Marker must be a regular file with exact mode 0600.
- Owner must equal the effective process owner.
- Link count must equal one.
- State size must match canonical acceptance bytes exactly.
- Redacted representation remains unchanged.
- No persistent representation is introduced.
