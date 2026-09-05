# LQ-2440 Post-rename evidence-readback gate

- The controller passes the exact canonical controlled-evidence payload to publication.
- After rename, the final path is opened with the existing no-follow evidence reader.
- Type, mode, owner, link count, size, bytes, and stable metadata are rechecked.
- Readback must equal the precommit payload byte for byte.
- Failure enters the identity-bound publication rollback boundary.
- A successful returned evidence path therefore names re-read final bytes.
