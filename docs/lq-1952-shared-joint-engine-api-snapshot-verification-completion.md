# LQ-1952 Shared joint engine API snapshot verification completion

- One helper invokes retained snapshot verifier.
- It accepts only normal none completion.
- Raw verifier return never reaches operation logic.
- Accept and accepted audit share the helper.
- Existing verifier remains provenance authority.
- No fallback success interpretation is available.
- No new port or verification model is introduced.
