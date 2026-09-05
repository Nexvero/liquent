# LQ-2424 Post-rebuild roundtrip-directory gate

- The sdist phase retains identity returned by private child creation.
- Rebuild completion is followed immediately by a no-follow identity check.
- Wheel discovery cannot begin if the build replaced or redirected its output root.
- Identity is checked again after byte equality and full wheel verification.
- Only then may the rebuilt wheel and parent identity enter shared gate state.
- Failure remains detail-limited and yields no successful sdist receipt.
