# LQ-1516 State-bound joint engine API accepted-source audit

- Audit captures source observation before marker verification.
- It compares a second complete observation after verification.
- Every child descriptor state participates in equality.
- Same-content transient source mutation is rejected.
- Both marker observations remain generation- and state-bound.
- Expected child-root identities remain unchanged.
- The operation and CLI surfaces do not expand.
