# LQ-2259 canonical sdist deflate byte contract

- One canonical Deflate representation binds the canonical TAR stream.
- Successful decompression and equal TAR bytes alone are insufficient.
- Alternate compression levels or block choices are rejected.
- The canonical profile is the local locked runtime's maximum compression.
- Header and trailer bytes remain governed by the prior envelope contract.
- Byte identity is required across repeated normalization runs.
- This contract grants no signing, upload, or publication authority.
