# LQ-2395 Distribution-artifact inventory contract

- The private `artifacts` directory contains exactly the bound wheel and source
  distribution and no third entry.
- Expected names and SHA-256 digests come from the measured distribution-pair state.
- Missing, additional, stale, temporary, or linked entries fail closed.
- Inventory facts bind each name, verified digest, and observed byte size.
- The inventory grants no publication or promotion authority.
