# LQ-1833 Joint engine API audit mode entry gate

- Mode validation is the first audit operation.
- Invalid input cannot consume verifier evidence.
- Invalid input cannot inspect registry persistence.
- Invalid input cannot initialize decision timing.
- Root resolution is never attempted for invalid mode.
- Direct callers receive detail-free rejection.
- Command-line behavior remains stable.
