# LQ-2168 Reproducible sdist normalizer

- The local release gate rewrites the built sdist deterministically.
- Every member receives the reviewed SOURCE_DATE_EPOCH.
- Numeric ownership is neutral and owner names are empty.
- Members are emitted in canonical name order.
- Gzip metadata uses the same fixed epoch and no source filename.
- Regular payload bytes and safe directory structure are preserved.
- Invalid epochs and unsafe archive members fail closed.
