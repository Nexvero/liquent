# LQ-2224 Wheel Requires-Dist gate

- Nine bounded runtime requirements are present in reviewed order.
- Four dev-extra requirements retain their exact markers and bounds.
- The visual extra contains only the bounded Streamlit requirement.
- Missing, additional, reordered, or respelled requirements fail closed.
- Provides-Extra is exactly dev followed by visual.
- Requires-External and Dynamic metadata are absent.
- Existing metadata-size and parser gates remain mandatory.
