# LQ-1488 Generation-bound joint engine API one-shot acceptance

- One-shot retains the observation returned by durable record.
- Existing value-only readback still verifies canonical marker value.
- A final marker observation verifies concrete generation continuity.
- Final observation retains expected acceptance-root binding.
- Source snapshot, time, duration, and cryptographic checks remain.
- The command-line and operation interfaces remain unchanged.
- Technical failures use the established unavailable result.
