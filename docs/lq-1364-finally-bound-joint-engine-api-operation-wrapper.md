# LQ-1364 Finally-bound joint engine API operation wrapper

- A shared wrapper resolves the complete operation boundary once.
- It invokes one supplied internal operation with that immutable binding.
- Final identity and metadata validation runs from a `finally` path.
- A successful operation result returns only after final validation.
- An inner failure propagates only after successful final validation.
- A final validation failure remains authoritative and fail closed.
- The wrapper introduces no public caller-supplied authority decision.
