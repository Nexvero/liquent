# LQ-2618 Release-evidence custody handoff

- Durable custody must retain the full candidate commit, source tree, image digest, and evidence-generation time.
- Preflight phase results, package roundtrip, image metadata, smoke result, and vulnerability report remain distinct records.
- Each record identifies its producing tool version and the immutable input it actually evaluated.
- Detached signatures and provider read-back receipts are added only after their authorized external actions succeed.
- Temporary paths under `/private/tmp` are local observations, not durable handoff locations.
- Secrets, private keys, raw credentials, DSNs, and sensitive provider responses are excluded from the evidence packet.
- Redaction must preserve decision status, identity bindings, and enough detail for independent verification.
- Missing, unreadable, altered, or identity-mismatched records fail closed at the consuming gate.
- Retention and access policy are owned by the external release authority.
- This slice neither uploads evidence nor chooses an external custody system.
