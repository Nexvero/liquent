# LQ-1671 Ordered joint engine API time finalization contract

- Initial UTC and monotonic values are captured first.
- Inner acceptance and all reobservations then execute.
- Final monotonic and UTC values are captured afterward.
- Clock ordering and duration are checked before freshness.
- Retained source verification follows valid clocks.
- Exact root validation completes successful return.
- Every step remains fail-closed.
