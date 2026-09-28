# LQ-2391 Fixed private workspace-directory contract

- Local gates may create only `artifacts`, `installed-wheel`,
  `sdist-wheel-roundtrip`, and `bundle` as workspace root directories.
- Caller-selected, empty, alternate, or additional names are rejected.
- Every allowed child is a current-user-owned directory with mode exactly 0700.
- The fixed set matches the terminal controlled-workspace inventory.
- No directory name grants publication or deployment authority.
