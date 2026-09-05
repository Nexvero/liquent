# LQ-2154 Joint engine API Unicode root completion

- LQ-2143 through LQ-2153 close Unicode root spelling.
- Encoding, NFC, categories, and authority compose.
- Every accepted CLI root is visible canonical Unicode.
- Public operation and persistence behavior remain stable.
- Focused verification passes 67 tests under strict warnings.
- Full local verification passes 6830 tests with 108 skips.
- Until external release evidence exists, production_ready=false.
