# LQ-2308 durable candidate-descriptor publication gate

- The temporary file is explicitly set to mode `0600` before writing.
- File bytes are flushed and synchronized before target publication.
- Exclusive same-directory hard-link creation prevents replacement.
- The temporary name is removed immediately after linking.
- The containing directory is synchronized before success returns.
- A failed directory sync rolls back only the newly linked target.
- Collision failure never removes a pre-existing target.
