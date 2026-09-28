# LQ-2515 Retained intermediate child-descriptor contract

- Every expected intermediate directory is opened from the workspace descriptor.
- The child open requires directory type and refuses symbolic-link traversal.
- Its descriptor remains held through relisting and terminal child verification.
- Captured identity is compared to descriptor metadata immediately after opening.
- A path lookup alone never substitutes for retained object continuity.
- Descriptor retention grants no publication, deployment, or external authority.
