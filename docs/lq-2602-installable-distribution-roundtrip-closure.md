# LQ-2602 Installable distribution roundtrip closure

- The release wheel now contains the closed `liquent`, `liquent_platform`, and `tools` package roots.
- All 71 declared console entry points load as callables from the isolated installed wheel.
- The wheel contains 456 bounded members and matches its reviewed canonical member-set digest.
- Its package metadata retains 71 entry points, 71 package modules, and 42 linear migrations.
- The enforced migration head is synchronized to `20260826_0042`.
- The normalized sdist binds source bytes from `src`, tests, and the packaged `tools` root.
- Generated egg-info metadata is verified at its deterministic root-relative location.
- The verified sdist is extracted only inside the private workspace before the roundtrip build.
- The rebuilt wheel is byte-identical to the directly built wheel.
- No artifact was signed, published, uploaded, promoted, or deployed.
