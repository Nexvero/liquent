# LQ-1413 Joint engine API acceptance pre-create root evidence

- Tests observe one pre-create and one post-write root validation.
- Missing visible parent before creation produces no marker.
- Parent symlink rebinding before creation produces no marker.
- Same-name real parent replacement before creation produces no marker.
- A forced pre-create rejection never opens the marker name.
- Validation descriptor closure has direct evidence.
- Focused verification treats deprecation warnings as failures.
