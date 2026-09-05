# LQ-2076 Joint engine API main completion gate

- Main independently requires dispatcher None.
- Dispatcher completion gate remains unchanged.
- Boolean false is not main completion.
- Numeric zero is not main completion.
- Empty containers are not main completion.
- Arbitrary payloads are not main completion.
- Invalid completion maps to status two.
