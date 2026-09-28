# LQ-1315 Joint engine API source root component contract

- Every source-root path component must resolve as a real directory.
- Symlinks are forbidden at the leaf and in every ancestor component.
- Absolute lexical input alone does not establish component trust.
- Traversal begins from an internally opened filesystem root descriptor.
- Each next component is opened relative to the preceding descriptor.
- Any missing, non-directory, or symlink component fails closed.
- The caller cannot provide pre-resolved descriptors or trust assertions.
