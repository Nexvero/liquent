# LQ-2283 source-bound distribution-pair contract

- A distribution pair is identified together with its source provenance.
- Provenance consists of the bound commit and its bound epoch.
- Equal artifact bytes from another source identity are a different pair.
- Equal names and version do not erase that provenance distinction.
- Commit and epoch come only from the preflight's immutable run state.
- The binding is evidence and grants no signing or publication authority.
- Persisted release registration remains a separate controlled boundary.
