# LQ-1429 Joint engine API one-shot identity binding evidence

- Tests observe the exact expected identity passed to durable record.
- The value equals the current registry device and inode.
- Canonical one-shot verification succeeds with that binding.
- Existing source mutation and marker mutation tests retain behavior.
- Existing failure-window wrappers forward the keyword binding unchanged.
- Standalone one-shot tests remain green without an expected identity.
- Focused evidence runs under strict warning handling.
