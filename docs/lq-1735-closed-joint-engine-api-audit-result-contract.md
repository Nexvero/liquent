# LQ-1735 Closed joint engine API audit result contract

- Audit handoff uses closed immutable result types.
- Registry and accepted-source results are distinct classes.
- Raw tags and positional mode dispatch are removed.
- Construction validates complete result semantics.
- Invalid results fail before outer success checks.
- Representations disclose no evidence detail.
- Public commands expose no result object.
