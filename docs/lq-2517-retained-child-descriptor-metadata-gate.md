# LQ-2517 Retained child-descriptor metadata gate

- Initial child facts come from metadata on the newly opened descriptor.
- Directory type, exact mode 0700, current owner, device, and inode are required.
- Device and inode must equal the controller-captured identity for that name.
- The same descriptor is measured again after the workspace relisting.
- Metadata drift on the retained object rejects the current verification.
- No changed fact is normalized, repaired, or adopted.
