# Staging Research end-to-end proof

This supervised operation proves one Research job from authenticated submission
through durable completion and artifact verification. It temporarily grants
`research:write` to the existing staging operator membership and always attempts
to restore the membership to `research:read` on exit.

1. Install `operations/research/staging-proof.sh` on the staging host.
2. Create `/etc/liquent/research-proof.env` from the checked-in example. Keep it
   root-owned and mode `0600`; it contains paths and container names, never secrets.
3. Review the owner-private base membership request. It identifies the exact
   actor, target user and workspace approved for the proof.
4. Run `LIQUENT_RESEARCH_PROOF_CONFIG=/etc/liquent/research-proof.env staging-proof.sh --check`.
5. After explicit operational approval, run the command without `--check` as root.

Success requires HTTP 202, a distinct durable job identifier, terminal
`succeeded`, non-empty evidence, exactly one claim and outcome, a byte-for-byte
artifact digest/size match, completed write revocation, and a final HTTP 403
`permission_denied` submission. Preserve the owner-private evidence directory.
If cleanup reports `write_permission_revocation=failed`, treat that as an incident
and revoke the permission with the membership-management runbook before any other
work.

Cleanup deletes the copied browser session, cookie and CSRF header files. It also
attempts revocation when grant confirmation retrieval fails: the revision is read
from the durable membership record, not the local grant result. A failed
revocation command must never be recorded as a successful revocation.
