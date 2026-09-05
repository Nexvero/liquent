# LQ-2483 Composite evidence-cleanup authority

- Cleanup requires an exact conjunction of workspace and created-file facts.
- Parent identity, parent privacy, parent ownership, child type, and child identity bind it.
- No single matching name, inode, mode, owner, or byte sequence is sufficient.
- Both controlled rejection branches pass the same measured identities.
- The decision is local, immediate, uncached, and never caller supplied.
- Failure to prove the full conjunction always chooses preservation.
