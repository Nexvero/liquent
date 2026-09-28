# LQ-2387 Controlled workspace-root inventory contract

- A successful controlled-preflight workspace has exactly five root entries:
  `artifacts`, `installed-wheel`, `sdist-wheel-roundtrip`, `bundle`, and
  `controlled-preflight.json`.
- Additional, missing, stale, or temporary root entries fail closed.
- Names and expected object kinds are fixed orchestration facts.
- Callers and gate receipts cannot expand the accepted inventory.
