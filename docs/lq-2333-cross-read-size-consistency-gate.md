# LQ-2333 Cross-read size consistency gate

- The expected size, descriptor size before reading, observed byte count, and
  descriptor size after reading must agree.
- The digest must independently equal the expected candidate digest.
- Candidate inventory facts contain the observed verified size and digest.
- Metadata or content drift during reading therefore cannot yield valid evidence.
- The result remains a local inventory identity rather than a signature.
