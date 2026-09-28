# LQ-2423 Roundtrip-directory continuity contract

- The fixed `sdist-wheel-roundtrip` path identifies one directory object throughout.
- Device and inode are bound when the private workspace child is created.
- Rebuilt-wheel digest equality cannot substitute for its parent identity.
- Replacement, path reuse, deletion and recreation, or redirection fail closed.
- The binding spans rebuild, byte comparison, wheel verification, and final inventory.
- This local custody evidence grants no publication or deployment authority.
