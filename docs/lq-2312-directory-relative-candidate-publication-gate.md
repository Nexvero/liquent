# LQ-2312 directory-relative candidate-publication gate

- The Bundle gate creates its output directory with mode `0700`.
- Candidate publication opens and retains that directory object.
- Opened device and inode must match the validated path identity.
- Exclusive link creation is relative to the held directory descriptor.
- Directory synchronization uses that same descriptor.
- Rollback unlinks only relative to that same held directory object.
- Concurrent outer-path replacement cannot retarget publication or rollback.
