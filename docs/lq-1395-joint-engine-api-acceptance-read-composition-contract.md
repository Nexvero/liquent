# LQ-1395 Joint engine API acceptance read composition contract

- Marker load composes one stable root and one stable marker decision.
- Registry inspection composes one stable root and stable full inventory.
- Both retain one working descriptor for all marker access.
- Both use one separate final descriptor only for root validation.
- Root and marker stability are jointly necessary for success.
- Neither read operation mutates registry contents.
- No alternate read mode or caller-configurable stability policy exists.
