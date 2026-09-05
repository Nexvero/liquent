# LQ-1839 Joint engine API mode-bound finalization contract

- Success callback retains the originally requested mode.
- It derives the only permissible result type from that mode.
- Exact type validation precedes evidence access.
- Registry checks cannot process accepted results.
- Accepted checks cannot process registry results.
- Technical rejection remains detail-free.
- Root final validation still follows every failure.
