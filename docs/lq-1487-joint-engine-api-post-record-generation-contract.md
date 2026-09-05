# LQ-1487 Joint engine API post-record generation contract

- One-shot acceptance must finish with the generation it recorded.
- Final marker observation must equal the record observation exactly.
- Equal canonical bytes in a new file are insufficient evidence.
- Registry-root continuity does not replace marker continuity.
- Source revalidation occurs between record and final observation.
- Any generation mismatch invalidates the acceptance outcome.
- Failure remains detail-free at the existing boundary.
