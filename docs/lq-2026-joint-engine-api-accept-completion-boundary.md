# LQ-2026 Joint engine API accept completion boundary

- Public Accept uses the completion runner.
- Private Accept sequencing remains unchanged.
- Valid completion returns None.
- Foreign success payloads fail closed.
- Durable acceptance is not exposed as a result.
- Failure normalization remains outermost.
- Signature remains unchanged.
