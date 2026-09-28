# LQ-1464 Bound joint engine API duplicate precheck

- Initial marker lookup receives expected acceptance-root identity.
- Root identity is checked before absence or marker bytes are trusted.
- Replacement with an empty identical-layout registry is rejected.
- Rejection occurs before verification and marker creation begin.
- Existing duplicate-marker verification behavior remains unchanged.
- The established unavailable result contains no filesystem details.
- Standalone calls without outer binding retain prior behavior.
