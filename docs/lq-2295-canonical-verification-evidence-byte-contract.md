# LQ-2295 canonical verification-evidence byte contract

- The terminal verification report has one canonical JSON byte form.
- Its source commit must equal the immutable preflight commit.
- Test counts must still match the captured quality-evidence digest.
- Final diff success is required before report rendering.
- Existing evidence keys and operational bundle schema remain unchanged.
- Report identity is SHA-256 of the complete canonical bytes.
- This evidence grants no signing, promotion, or publication authority.
