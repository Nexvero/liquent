# LQ-2148 Composed joint engine API Unicode root policy

- Exact string type precedes UTF-8 encoding.
- UTF-8 encoding precedes NFC and category policy.
- NFC and category policy precede component bounds.
- Native Path construction remains downstream.
- Namespace and dispatch receive canonical text only.
- Root resolution remains authority.
- No persistence behavior changes.
