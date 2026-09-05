# LQ-1787 Joint engine API terminal inventory sequencing contract

- Final source freshness verification completes first.
- Terminal source equality is then confirmed.
- The created run marker is reobserved next.
- Complete registry inventory is reobserved after that.
- Terminal monotonic time closes the sequence.
- Every step remains inside one operation-root sandwich.
- Sequence failure prevents success.
