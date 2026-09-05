# LQ-1301 Joint engine API bounded layout evidence

- Parameterized tests cover all supported layout generations.
- They prove normal per-source limits remain exactly unchanged.
- They prove constrained child two receives only remaining bytes.
- They prove exact exhaustion prevents child two from opening.
- They prove zero allowance prevents even child one from opening.
- Previous exact-total and one-byte-short aggregate tests remain green.
- Focused evidence totals 35 passing tests under strict warnings.
