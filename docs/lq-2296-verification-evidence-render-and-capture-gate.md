# LQ-2296 verification-evidence render-and-capture gate

- One pure renderer validates provenance and quality before serialization.
- It emits the existing commit, test, version, and gate facts canonically.
- The Bundle gate writes those bytes exactly once to verification.json.
- It immediately rereads and hashes the written file.
- The resulting digest is stored in private preflight run state.
- Caller-provided report bytes or report digests are not accepted.
- Failure is detail-limited and prevents bundle construction.
