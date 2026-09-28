# LQ-1463 Joint engine API duplicate precheck binding contract

- Duplicate detection is a decision on the resolved acceptance registry.
- Its marker lookup must verify registry identity before reading state.
- Absence in a replacement registry cannot authorize marker creation.
- Presence in the bound registry still rejects repeated acceptance.
- The check supplies no authority beyond its observed marker state.
- Mismatch and malformed state remain detail-free failures.
- No retry or alternate registry lookup is allowed.
