# LQ-2244 sdist SOURCES manifest gate

- SOURCES.txt is strict UTF-8 with LF separators and no terminal separator.
- Every source line is unique.
- Its set equals the complete archive file set minus two generated root files.
- Missing, additional, duplicate, or malformed source lines fail closed.
- Archive topology and source-byte binding remain independently mandatory.
- Ordering remains backend-generated and is retained byte-for-byte.
- No filesystem extraction is used for verification.
