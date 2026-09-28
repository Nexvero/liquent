# LQ-1427 Joint engine API one-shot identity binding contract

- One-shot acceptance may receive the expected acceptance-root identity.
- It forwards that exact value only to durable marker record.
- Source verification and marker precheck retain existing behavior.
- The identity does not alter cryptographic or acceptance decisions.
- A mismatch rejects before the one-shot marker write.
- Later source and marker revalidation remain mandatory after success.
- No identity cache or alternate-root retry is added.
