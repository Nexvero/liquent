# LQ-2167 Reproducible sdist contract

- A reviewed source and SOURCE_DATE_EPOCH determine sdist bytes.
- Build-clock time must not survive in archive metadata.
- File names, modes, and payloads remain source-derived facts.
- Archive ordering is canonical and independent of traversal order.
- Links and special members fail closed during normalization.
- The contract adds no publication or promotion authority.
- External release evidence remains separately required.
