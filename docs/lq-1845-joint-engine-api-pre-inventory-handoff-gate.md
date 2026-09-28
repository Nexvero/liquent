# LQ-1845 Joint engine API pre-inventory handoff gate

- Handoff type is checked immediately after mutation call.
- Invalid type stops before final inventory observation.
- Invalid evidence cannot influence delta comparison.
- Invalid evidence cannot enter closed result construction.
- Root final validation still runs on failure.
- Durable mutation outcome remains preserved when present.
- No hidden cleanup or retry is added.
