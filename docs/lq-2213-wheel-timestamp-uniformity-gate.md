# LQ-2213 Wheel timestamp uniformity gate

- The first bounded member establishes one archive timestamp fact.
- Every later member must carry exactly that same timestamp.
- The timestamp is representable by the ZIP epoch and two-second clock.
- Odd-second aliases fail rather than being silently rounded.
- Payload and RECORD identity remain independent of timestamp metadata.
- Direct and sdist-roundtrip wheels cross the same check.
- Exact SOURCE_DATE_EPOCH binding remains a separate composition fact.
