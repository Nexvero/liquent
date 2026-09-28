# LQ-2059 Joint engine API closed CLI dispatch contract

- CLI dispatch accepts exactly three mode strings.
- Each mode maps to one fixed operation.
- Each dispatch invokes exactly one operation.
- Successful operation result must be exactly None.
- Foreign results fail closed.
- Invalid modes invoke no operation.
- Public CLI syntax remains unchanged.
