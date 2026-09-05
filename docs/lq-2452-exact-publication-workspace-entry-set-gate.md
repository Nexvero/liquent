# LQ-2452 Exact publication workspace-entry-set gate

- Child verification begins with the exact five-entry workspace inventory.
- The set contains four fixed directories and controlled preflight evidence only.
- Missing, additional, stale, or temporary root entries fail before child opens.
- The same sorted entry list is measured again after every child is opened.
- Concurrent entry insertion, removal, or rename therefore fails closed.
- Caller-selected names cannot enter the retained child identity map.
