# LQ-2447 Terminal publication-metadata contract

- Publication identity includes private root metadata through successful return.
- Device and inode equality cannot substitute for mode and ownership checks.
- The common parent and published workspace must each remain mode 0700.
- Both must remain owned by the current local user.
- Terminal metadata drift fails closed inside the rollback-capable boundary.
- These local privacy facts grant no deployment or external publication authority.
