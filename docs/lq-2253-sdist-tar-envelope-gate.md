# LQ-2253 sdist TAR envelope gate

- The gate derives logical end from parsed member offsets and sizes.
- It rounds each payload to the TAR block boundary fail closed.
- Expected archive length is the minimal enclosing 10-KiB record.
- Both end-marker blocks must contain only zero bytes.
- Every byte after those markers must also be zero.
- Extra records and nonzero padding are rejected before manifest acceptance.
- Rejection is detail-limited and does not rewrite the candidate.
