# LQ-2064 Joint engine API CLI completion gate

- Dispatcher independently checks exact None.
- Direct API completion checks remain unchanged.
- Boolean false is not CLI completion.
- Numeric zero is not CLI completion.
- Empty containers are not CLI completion.
- Arbitrary payloads are not CLI completion.
- Invalid completion maps to status two.
