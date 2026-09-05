# LQ-2195 sdist wheel roundtrip contract

- The normalized sdist must independently rebuild the reviewed wheel.
- Rebuilding uses the locked local backend without build isolation.
- The direct wheel and sdist-derived wheel are byte-identical.
- Filename similarity or metadata similarity is insufficient.
- The rebuilt wheel passes the existing wheel verifier independently.
- Failure rejects the sdist phase before later bundle work.
- The contract adds no publication, signing, or installation authority.
