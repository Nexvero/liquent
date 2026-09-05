# LQ-2157 Joint engine API CLI root text composition

- Raw CLI parser delegates text policy once.
- Valid text then constructs native Path.
- Native Path preflight independently closes result.
- Existing Namespace handoff remains unchanged.
- Existing dispatch remains unchanged.
- Invalid text remains status two and silent.
- No duplicate text policy remains.
