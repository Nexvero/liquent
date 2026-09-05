# LQ-2416 Post-install root-identity gate

- The entry-point phase retains identity returned by private child creation.
- Successful Pip completion is followed immediately by a no-follow identity check.
- Loading cannot begin if installation replaced or redirected the target directory.
- The target must still be current-user-owned, mode 0700, and a real directory.
- A matching path string is insufficient when device or inode differs.
- Failure remains detail-limited and produces no successful phase receipt.
