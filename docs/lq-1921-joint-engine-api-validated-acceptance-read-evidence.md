# LQ-1921 Joint engine API validated acceptance read evidence

- Tests observe one shared marker read in accept.
- Malformed terminal accept marker is rejected.
- Tests observe two outer reads in accepted audit.
- Malformed marker is rejected at either audit stage.
- Run and root identities remain stable on every read.
- Registry audit performs no target-marker read.
- All focused warnings are treated as errors.
