# LQ-1967 Joint engine API acceptance builder type gate

- Canonical authority enters existing acceptance builder.
- Retained source envelope is passed unchanged.
- Builder result must have exact acceptance runtime type.
- Bare, null, or foreign results fail closed.
- Successful value retains source-derived run identity.
- No caller allow boolean or role participates.
- Existing acceptance semantics remain unchanged.
