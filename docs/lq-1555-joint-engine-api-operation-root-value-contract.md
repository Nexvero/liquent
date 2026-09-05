# LQ-1555 Joint engine API operation root value contract

- Operation roots form one closed two-child filesystem topology.
- Source and acceptance paths must be safe and absolute.
- Both paths must be siblings under one parent.
- Fixed child names are mandatory.
- Root and child identities must be distinct.
- Invalid values fail through the unavailable boundary.
- The value grants no caller authority.
