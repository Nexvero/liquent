# LQ-2435 Post-rename failure atomicity contract

- A failed post-rename identity check must not leave a successful output name.
- Recovery may move only the same bound workspace directory object.
- Existing source or foreign output entries are never overwritten or removed.
- Rollback uses the already bound parent descriptor and fixed relative names.
- Failure remains detail-limited regardless of whether safe rollback is possible.
- This recovery changes no deployment or external publication semantics.
