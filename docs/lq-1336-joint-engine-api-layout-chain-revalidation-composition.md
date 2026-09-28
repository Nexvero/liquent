# LQ-1336 Joint engine API layout chain revalidation composition

- Each loader acquires its root through the shared initial component walk.
- Each performs its established bounded layout-specific source capture.
- Shared final validation repeats the complete component walk.
- Initial, held-final, and visible-final root facts must all agree.
- Successful output composition remains layout-specific and immutable.
- Both traversal descriptors remain internally owned and closed.
- No CLI, configuration, or cryptographic behavior changes.
