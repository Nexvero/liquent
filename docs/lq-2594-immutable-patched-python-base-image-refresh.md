# LQ-2594 Immutable patched Python base-image refresh

- The existing Python 3.13.15 slim-trixie digest contained OpenSSL 3.5.6.
- Grype found nine fixable High/Critical CVEs across three OpenSSL packages.
- The official tag now resolves to patched immutable digest `9d2e5553...00285`.
- Dockerfile changes only that complete sha256 base-image pin.
- The image-gate assertion records the same exact digest.
- No mutable `apt upgrade`, vulnerability ignore, or risk exception was added.
- Fourteen container and supply-chain invariant tests passed after the update.
- The rebuilt local image completed successfully.
