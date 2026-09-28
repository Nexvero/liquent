# LQ-2132 Joint engine API CLI root byte policy

- Bounds apply to UTF-8 bytes, not character count.
- Total path excludes no supplied character.
- Component bytes are measured independently.
- Multibyte text consumes its exact encoded size.
- Limits are private stable constants.
- No filesystem limit lookup occurs.
- No caller limit override exists.
