# LQ-1461 Joint engine API one-shot acceptance read evidence

- Instrumented tests observe registry identity on both marker reads.
- The exact identity preserves successful one-shot acceptance.
- An identically copied replacement fails the initial read.
- Existing source and write identity tests remain green.
- Unbound standalone acceptance remains regression-covered.
- Strict warning treatment guards interface compatibility.
- Local evidence does not replace external runtime attestation.
