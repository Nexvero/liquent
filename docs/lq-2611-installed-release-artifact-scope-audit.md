# LQ-2611 Installed release-artifact scope audit

- The wheel contains only the closed roots `liquent`, `liquent_platform`, `tools`, and its dist-info directory.
- The reviewed member set contains exactly 456 bounded entries.
- Source payload verification compares every packaged Python and Mako byte with the repository source.
- RECORD coverage, digest, size, timestamp, compression, metadata, and entry-point gates remain fail closed.
- All 71 console entry points load from the isolated wheel and final container image.
- The sdist includes the same package roots plus reviewed tests and deterministic generated metadata.
- A wheel rebuilt from the normalized sdist is byte-identical to the direct wheel.
- Documentation, operations, secrets, raw data, and processed data are absent from the runtime wheel.
- Artifact installability grants no signer, publisher, staging, or deployment authority.
