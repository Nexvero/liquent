# LQ-1807 Joint engine API accepted audit evidence shape contract

- Accepted-source audit requires one exact evidence tuple.
- The tuple contains exactly source and marker observations.
- Null, empty, partial, or oversized evidence is rejected.
- Lists and other iterable shapes are not accepted.
- Shape validation precedes closed result construction.
- Failure remains detail-free.
- Public audit behavior remains unchanged.
