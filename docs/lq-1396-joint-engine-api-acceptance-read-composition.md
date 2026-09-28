# LQ-1396 Joint engine API acceptance read composition

- Load validates run identity before root acquisition.
- It reads one named marker through the held root descriptor.
- Inspection captures names and all markers through its held descriptor.
- Each read path then performs complete final root-state validation.
- Existing marker metadata and canonical codec checks remain unchanged.
- Final visible-root traversal never performs marker reads.
- Errors retain the existing detail-free conversion boundary.
