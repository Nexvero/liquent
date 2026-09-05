# LQ-2140 Detail-free joint engine API root bound rejection

- Rejection reveals no encoded length.
- It reveals no oversized component.
- It reveals no control character.
- It reveals no encoding failure detail.
- Main exposes status two only.
- Stdout and stderr remain empty.
- No diagnostic fallback exists.
