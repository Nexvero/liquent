# LQ-2054 Joint engine API CLI parser audit

- Standard parser diagnostics no longer escape.
- Permitted mode inventory remains private on rejection.
- Supplied root text remains private on rejection.
- Main catches parser and operation failures uniformly.
- Successful commands remain silent.
- No retry or interactive prompt exists.
- No durable layout changes.
