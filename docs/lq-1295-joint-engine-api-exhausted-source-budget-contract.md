# LQ-1295 Joint engine API exhausted source budget contract

- Zero remaining aggregate bytes cannot authorize another child open.
- Exhaustion is checked before invoking the descriptor-relative reader.
- A nonempty canonical source still remaining therefore rejects closed.
- No path lookup, open, read, or child allocation follows exhaustion.
- Exact exhaustion is successful only when no canonical source remains.
- The rule depends solely on fixed layout order and observed byte lengths.
- Rejection remains detail-free technical unavailability.
