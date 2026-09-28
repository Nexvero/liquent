# LQ-1348 Joint engine API operation boundary composition

- Resolution opens the operation root through its real component chain.
- It captures both fixed child identities descriptor-relatively.
- Final root traversal and final child reads revalidate all identities.
- Only then is the immutable operation-root value constructed.
- Existing accept, audit, and identity validation consume that value.
- Command-line exposure remains one operation root and closed modes.
- No cryptographic or acceptance-registry semantics change.
