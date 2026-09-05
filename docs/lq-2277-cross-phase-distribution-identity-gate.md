# LQ-2277 cross-phase distribution-identity gate

- Every pair recheck derives names, version, and digests again from files.
- Current facts must equal every captured build-phase identity component.
- The combined pair digest is also recalculated and compared.
- Wheel, sdist, and bundle phases share this single check.
- A rename, version split, or byte replacement rejects fail closed.
- Failure reveals no differing component outside the local gate.
- The check performs no mutation or artifact replacement.
