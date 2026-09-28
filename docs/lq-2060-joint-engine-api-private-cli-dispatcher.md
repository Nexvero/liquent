# LQ-2060 Joint engine API private CLI dispatcher

- One private dispatcher owns mode routing.
- It receives parsed root and mode only.
- It performs no parsing itself.
- It performs no output itself.
- It returns None after valid completion.
- It reuses unavailable failure.
- No public port is added.
