# LQ-2347 Bound candidate-identity input contract

- Candidate identity accepts the sealed bundle and canonical verification report
  only when both reside in the same private output directory.
- That parent is resolved to a stable device and inode before either input is read.
- Input names come from the locally produced artifacts, not caller aliases.
- A cross-directory mixture is rejected without identity generation.
- The resulting identity remains local and non-promotable.
