# LQ-2415 Installed-root continuity contract

- The fixed `installed-wheel` path must identify one directory object throughout.
- Device and inode are bound when the private workspace child is created.
- Path reuse, replacement, deletion and recreation, or symbolic redirection fail closed.
- The binding spans installation, isolated loading, tree measurement, and bundle gating.
- Content identity remains a separate digest and cannot substitute for root identity.
- The bound directory remains local evidence and grants no deployment authority.
