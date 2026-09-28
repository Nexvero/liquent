# LQ-2144 Joint engine API root NFC gate

- NFC comparison uses the full supplied string.
- Accepted text is byte-for-byte retained.
- Decomposed equivalent spelling is rejected.
- Composed canonical spelling remains accepted.
- No NFD, NFKC, or NFKD fallback exists.
- No normalized replacement is returned.
- Existing unavailable failure is reused.
