# LQ-1640 Final joint engine API inventory result

- Accept operation retains its final observation tuple.
- The tuple follows exact delta validation.
- It includes preserved and newly created generations.
- Internal wrapper receives the immutable tuple.
- Public command behavior remains no-result success.
- No serialization or new interface is introduced.
- Failure returns no evidence.
