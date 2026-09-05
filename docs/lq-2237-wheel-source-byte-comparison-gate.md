# LQ-2237 Wheel source byte-comparison gate

- Exact source and wheel name-set equality is checked first.
- Every accepted name is then read from both bounded wheel and source.
- Byte equality is required without normalization or compilation.
- Direct and sdist-roundtrip wheels compare against the same source root.
- RECORD remains an independent wheel-internal byte binding.
- Build-backend identity remains independently mandatory.
- Any mismatch uses the existing wheel verification rejection.
