# LQ-2191 Cross-phase sdist binding contract

- Distribution verification establishes one immutable sdist manifest.
- The manifest remains private state of the same preflight run.
- The later sdist phase rechecks the artifact against those exact facts.
- A path alone is not sufficient continuity evidence.
- Replacement or mutation between phases fails closed.
- No caller may supply a substitute manifest or root assertion.
- The contract adds no publication or promotion authority.
