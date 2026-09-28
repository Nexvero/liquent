# LQ-2512 Terminal intermediate root-metadata gate

- The workspace descriptor is measured again after both child passes.
- Terminal device and inode must equal the controller-bound workspace identity.
- Exact mode 0700 and current local ownership remain mandatory.
- Root metadata drift during child verification fails the same invocation.
- The open descriptor prevents path substitution from becoming trusted state.
- Later gates cannot legitimize a failed terminal root measurement.
