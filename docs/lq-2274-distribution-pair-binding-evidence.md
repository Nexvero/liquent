# LQ-2274 distribution-pair binding evidence

- Tests accept the exact captured wheel and sdist pair.
- Independent wheel replacement is rejected fail closed.
- Independent sdist replacement is rejected fail closed.
- Existing sdist roundtrip still requires byte equality with the wheel.
- Existing canonical reconstruction protects both captured byte identities.
- The bundle phase rechecks the pair before constructing evidence.
- External signing and publication evidence remain open; production_ready=false.
