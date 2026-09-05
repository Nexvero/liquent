# LQ-2420 Post-build distribution-directory gate

- The build phase retains identity returned by private child creation.
- Build completion is followed immediately by a no-follow identity check.
- Artifact discovery cannot begin if the build replaced or redirected its output root.
- The same identity is checked again after normalization and pair measurement.
- Only then may the wheel, sdist, and parent identity enter shared gate state.
- Failure remains detail-limited and yields no successful distribution receipt.
