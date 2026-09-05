# LQ-2486 Pre-rollback parent-identity gate

- Rollback first measures the already open common parent descriptor.
- Its device and inode must equal the preflight's retained parent identity.
- Its owner must still be the current user.
- These checks precede source-absence and output-identity inspection.
- Failure returns false without rename, unlink, chmod, or alternate path access.
- Both publication exception branches supply the same retained parent identity.
