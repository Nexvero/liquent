# LQ-2024 Shared joint engine API completion runner

- One private runner composes execution and completion.
- It reuses the detail-free runner.
- It accepts only the None singleton.
- It returns None after valid completion.
- It performs no retry.
- It performs no persistence work itself.
- No public port is added.
