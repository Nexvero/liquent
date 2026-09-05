# LQ-2047 Joint engine API detail-free CLI parser contract

- Invalid CLI input returns status two.
- Invalid CLI input writes no stdout.
- Invalid CLI input writes no stderr.
- Usage text is not emitted.
- Argument details are not emitted.
- Valid arguments retain existing behavior.
- Public argument names remain unchanged.
