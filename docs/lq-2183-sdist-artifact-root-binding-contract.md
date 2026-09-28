# LQ-2183 sdist artifact root binding contract

- The artifact basename determines one exact package root.
- Accepted artifacts use the form liquent-<version>.tar.gz.
- Version spelling is bounded to package-safe ASCII characters.
- Every member belongs to the root derived from that basename.
- The root itself exists exactly once as a directory member.
- Missing, mismatched, or file-shaped roots fail closed.
- No caller supplies a separate expected-root assertion.
