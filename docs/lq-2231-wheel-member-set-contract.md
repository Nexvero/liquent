# LQ-2231 Wheel member-set contract

- Release preflight accepts one exact reviewed wheel pathname set.
- Additional executable or data members are not implicitly trusted.
- Member count and sorted-name digest are independent required facts.
- The allowed top-level roots are liquent, liquent_platform, and dist-info.
- top_level.txt declares exactly the two importable package roots.
- Missing, additional, renamed, or foreign members fail closed.
- The contract adds no import, installation, or publication authority.
