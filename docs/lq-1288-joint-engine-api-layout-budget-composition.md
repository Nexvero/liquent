# LQ-1288 Joint engine API layout budget composition

- Policy-, image-, and run-bound loaders call one cumulative loader.
- Each supplies its existing canonical ordered names and size limits.
- Additional authority sources are counted before the common base sources.
- Successful loading preserves each existing immutable snapshot shape.
- Aggregate accounting does not reinterpret provenance or signatures.
- Existing root stability checks run only after complete bounded capture.
- The composition introduces no alternate source-layout discovery.
