# LQ-2445 Terminal publication-namespace gate

- After final-path readback, the parent device and inode are checked again.
- The temporary workspace relative name must be absent.
- The output relative name must be a real directory with workspace identity.
- These checks use the still-open bound parent descriptor without following links.
- Namespace drift triggers the same identity-bound rollback attempt and rejection.
- Publication returns only after durable rename and terminal namespace binding.
