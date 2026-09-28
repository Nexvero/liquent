# LQ-2039 Joint engine API audit mode preflight

- Audit validates mode before root shape.
- Mode runtime type must be exact bool.
- Integer aliases are not accepted.
- Invalid mode triggers no clock read.
- Invalid mode triggers no root resolution.
- Both valid modes retain existing behavior.
- Signature remains unchanged.
