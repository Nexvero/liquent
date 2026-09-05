# LQ-2305 candidate-descriptor verification gate

- The terminal gate rereads the descriptor after atomic creation.
- Symlinks, missing files, and non-files reject fail closed.
- Every byte must equal canonical rendering of the candidate facts.
- The byte digest must equal the derived release-candidate SHA-256.
- Successful phase facts expose only the basename and digest.
- Verification does not rewrite a mismatching descriptor.
- Bundle status remains explicitly `promotable=false`.
