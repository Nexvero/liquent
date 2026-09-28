# LQ-2432 Descriptor-bound precommit child gate

- Publication opens the workspace relative to the already bound parent descriptor.
- Its device and inode must equal the retained workspace identity.
- All four child identities are checked through that open workspace descriptor.
- The checks occur inside the publication operation immediately before rename.
- Missing, redirected, replaced, non-private, or foreign-owned children fail closed.
- Relative rename cannot start unless the complete identity set passes.
