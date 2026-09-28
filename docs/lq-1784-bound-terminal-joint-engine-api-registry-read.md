# LQ-1784 Bound terminal joint engine API registry read

- Terminal inventory uses the resolved acceptance root.
- The original acceptance-root identity remains mandatory.
- Caller-selected paths or identities are never accepted.
- The existing bounded registry observer performs the read.
- Complete immutable marker observations are returned.
- Root replacement fails through the existing boundary.
- No new storage interface is introduced.
