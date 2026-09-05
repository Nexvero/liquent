# LQ-1363 Joint engine API operation failure revalidation contract

- Operation-root state is revalidated after success and inner failure.
- An inner exception cannot bypass final root and child observations.
- The initially resolved immutable binding remains the comparison baseline.
- Root, source, or acceptance replacement on a failure path fails closed.
- Successful and failed operations share one final validation policy.
- No retry or fresh-baseline resolution follows inner failure.
- Command boundaries continue to expose only their closed status result.
