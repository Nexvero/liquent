# LQ-1491 Joint engine API operation recorded generation contract

- Operation accept requires stable roots and recorded marker generation.
- Resolved acceptance identity constrains precheck, write, and reads.
- Record descriptor identifies the marker generation actually created.
- Final observation must identify that same generation.
- Resolved source identity constrains both source observations.
- Any mismatch fails without caller-controlled fallback.
- Outer operation-root revalidation remains independently required.
