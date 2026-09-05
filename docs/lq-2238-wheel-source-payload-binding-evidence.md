# LQ-2238 Wheel source-payload binding evidence

- Tests accept an exact materialized package source tree.
- Tests reject changed, missing, and additional source payloads.
- Tests reject symlinked package roots.
- Real wheels match all 417 reviewed package payloads byte-for-byte.
- Member set, entries, metadata, RECORD, ZIP, and bounds remain composed.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
