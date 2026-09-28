# LQ-2606 Installed offline release CLI evidence

- Eight release control-plane commands were loaded directly from the final local image.
- Registry bootstrap, key activation, signing, and promotion exposed their fixed help surfaces.
- Publication bootstrap, executor, handoff, and publication exposed their fixed help surfaces.
- Every command exited successfully without opening a database or contacting a provider.
- The check used image `sha256:ea42ec6172063b0ee06afc3455801af4e0b0cc23785e95beb7f49a1179ecc8eb`.
- The image remains bound to code commit `d273c9af6b8cb5ad62fed399821b5570beef906b`.
- CLI availability proves installability only, not authority or environment readiness.
- No request file, DSN, key, credential, registry record, or provider target was supplied.
- No signing, promotion, publication, staging, or deployment side effect occurred.
