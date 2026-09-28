# LQ-2120 Joint engine API raw root parser

- One private parser owns raw root spelling.
- It validates text before constructing Path.
- It constructs one Path after valid spelling.
- It reuses direct root validation.
- It performs no filesystem operation.
- It performs no clock read.
- No public parser API is added.
