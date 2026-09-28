# LQ-2569 Distinct intermediate identity-map contract

- Each expected phase-output name binds one distinct filesystem identity.
- Two different names may not claim the same device and inode tuple.
- Every key is an exact string from the fixed phase-output vocabulary.
- Key and identity uniqueness are decided from the entry-time snapshot.
- Invalid mappings reject before workspace opening or namespace observation.
- Mapping validity grants no publication, deployment, or release authority.
