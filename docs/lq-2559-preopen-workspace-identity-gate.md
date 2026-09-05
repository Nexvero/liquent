# LQ-2559 Preopen workspace-identity gate

- The bound workspace identity is validated before workspace opening.
- Invalid shape, type, or sign causes immediate controlled rejection.
- No root descriptor, child descriptor, or directory listing is attempted.
- The supplied path cannot compensate for an invalid identity fact.
- A later metadata match cannot rehabilitate rejected input.
- Existing detail-limited failure text remains unchanged.
