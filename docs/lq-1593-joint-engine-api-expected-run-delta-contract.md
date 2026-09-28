# LQ-1593 Joint engine API expected run delta contract

- Added marker run ID must equal observed source run ID.
- A different canonical run marker cannot satisfy the delta.
- Filename and payload canonicality remain inspector responsibilities.
- Source run authority remains cryptographically verified inside one-shot.
- Expected run is never a caller argument.
- Failure does not identify either run.
- No alternate run marker is accepted.
