# LQ-2245 sdist-wheel metadata parity gate

- Both PKG-INFO copies equal each other and wheel METADATA.
- Egg-info entry_points.txt equals the verified wheel entry-point file.
- Egg-info top_level.txt equals the verified wheel top-level file.
- dependency_links.txt is one empty LF line.
- requires.txt and setup.cfg match fixed canonical payloads.
- Distribution and late sdist phases require the same metadata digest.
- Any redundant-fact disagreement fails closed.
