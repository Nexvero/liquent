# LQ-1680 Completion-bound joint engine API freshness

- Retained source is verified at verification time first.
- Completion UTC is captured after source convergence.
- The same snapshot is verified again at completion UTC.
- Policy freshness applies independently to both times.
- Snapshot object identity remains unchanged.
- No reload substitutes later source bytes.
- Expiration at completion fails success.
