# LQ-2179 Canonical sdist metadata contract

- Accepted names are already NFC and contain no Unicode control category.
- Regular package files have exactly mode 0644.
- Package directories have exactly mode 0755 and zero declared bytes.
- Privileged, executable, private, and world-writable aliases fail closed.
- Extended metadata is limited to exact long paths and bounded source time.
- Metadata is validated before payload retention and rewrite.
- The contract grants no installation or execution authority.
