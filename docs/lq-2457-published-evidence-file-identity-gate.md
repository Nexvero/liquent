# LQ-2457 Published evidence-file identity gate

- Publication receives the retained evidence identity with the exact payload.
- Final-path no-follow readback requires matching device and inode before reading.
- The following full workspace inventory checks the same evidence identity again.
- A byte-identical file at a new inode cannot produce publication success.
- Failure remains inside the identity-bound rollback-capable publication boundary.
- Successful return names the originally verified evidence file object.
