# LQ-2185 sdist root directory composition

- Filename validation runs before archive parsing.
- Topology validation receives the internally derived expected root.
- The first observed root and every later member must match it.
- One explicit directory member establishes the package root.
- Existing mode, Unicode, PAX, topology, and size gates still apply.
- Deterministic rewrite runs only after complete root binding.
- The original artifact remains unchanged on rejection.
