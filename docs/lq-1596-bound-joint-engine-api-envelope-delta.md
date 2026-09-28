# LQ-1596 Bound joint engine API envelope delta

- Expected acceptance includes canonical envelope SHA-256.
- Final added value must equal that complete object.
- Same-run marker with altered canonical hash is rejected.
- Marker decoder and observation semantics remain mandatory.
- Registry state exception follows only after exact equality.
- No persistent expected-value cache is introduced.
- CLI behavior remains unchanged.
