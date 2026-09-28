# LQ-2232 Wheel top-level root gate

- Every member belongs to one of three identity-bound roots.
- The dist-info root is derived from filename and metadata version.
- Import roots are exactly liquent and liquent_platform.
- top_level.txt exists in the same dist-info root.
- Its bytes are exactly liquent newline liquent_platform newline.
- Foreign roots and alternate top-level declarations fail closed.
- Existing path topology and RECORD checks remain mandatory.
