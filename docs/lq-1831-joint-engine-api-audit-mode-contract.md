# LQ-1831 Joint engine API audit mode contract

- Audit mode is one exact boolean value.
- False selects complete registry audit.
- True selects accepted-source audit.
- Integers and other truthy values are rejected.
- No coercion or normalization selects a mode.
- Invalid mode fails closed without detail.
- CLI mode mapping remains unchanged.
