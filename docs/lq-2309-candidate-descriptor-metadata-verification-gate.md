# LQ-2309 candidate-descriptor metadata verification gate

- Verification uses non-following filesystem metadata inspection.
- It requires regular-file type, mode `0600`, and link count one.
- Recorded file size must stay within the descriptor size contract.
- Exact canonical bytes and candidate digest are then checked again.
- Mode, type, link, size, byte, or digest drift rejects fail closed.
- Rejection performs no repair or replacement of the candidate.
- Successful Bundle facts remain explicitly non-promotable.
