# LQ-2466 Bound evidence-writer workspace evidence

- Focused tests replace a bound workspace with a fresh same-named private directory.
- The identity-aware writer rejects before creating controlled evidence there.
- Source checks retain expected identity before and after synchronized writing.
- Controlled execution passes the identity captured at workspace creation.
- Existing exclusive file, readback, inventory, publication, and rollback checks remain.
- Production readiness remains false; deployment and external publication remain forbidden.
