# LQ-1472 Joint engine API marker observation value

- The immutable observation contains acceptance and marker identity.
- Construction requires the exact established acceptance value type.
- Identity rejects booleans, negatives, and malformed tuple shapes.
- Representation reveals neither marker content nor filesystem facts.
- Equality includes both decoded value and concrete file identity.
- The value introduces no persistence or mutation behavior.
- Technical invalidity uses the existing unavailable result.
