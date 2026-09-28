# LQ-2535 Second capture-namespace gate

- The fixed visible child name is resolved a second time without link following.
- Its terminal identity must equal the original held child descriptor identity.
- Its type, exact private mode, and current ownership remain mandatory.
- Replacement after the first namespace lookup therefore fails closed.
- The terminal name is never permitted to select a new trusted identity.
- No callback or receipt parsing occurs between capture observations.
