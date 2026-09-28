# LQ-1344 Final joint engine API operation child revalidation

- One helper owns private child opening and identity extraction.
- Initial identities are captured relative to the held operation root.
- Final identities are captured relative to the re-opened visible root.
- Both ordered identity tuples must match exactly.
- Child descriptors close immediately after each identity observation.
- Final inventory checks precede final child opens.
- Revalidation completes before the immutable binding is returned.
