# LQ-1375 Joint engine API acceptance root component contract

- Every acceptance-root component must be a real directory.
- Parent and leaf symlinks fail before marker access or creation.
- Traversal starts from an internally opened filesystem-root descriptor.
- Every next segment opens descriptor-relatively with no-follow semantics.
- Existing owner-private acceptance-root checks remain mandatory.
- Callers cannot provide trusted descriptors or resolved-target assertions.
- Failure remains detail-free registry unavailability.
