# LQ-2441 Post-rename workspace-inventory gate

- Final-path evidence readback is followed by full workspace inventory verification.
- The exact five entries, their types, private modes, ownership, and bounds remain required.
- All four directory entries must still match their captured device and inode.
- The published root must still match the retained workspace identity.
- Inventory failure uses the same safe rollback path as other post-rename failures.
- Publication returns only after final-path evidence and inventory both pass.
