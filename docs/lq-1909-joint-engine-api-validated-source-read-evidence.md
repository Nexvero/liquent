# LQ-1909 Joint engine API validated source read evidence

- Tests observe four shared source reads in accept.
- Malformed source is rejected at each accept stage.
- Tests observe two outer reads in accepted audit.
- Every operation read preserves bound source identity.
- Registry audit performs no source read.
- Valid stable source still completes.
- All focused warnings are treated as errors.
