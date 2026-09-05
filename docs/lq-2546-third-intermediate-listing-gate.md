# LQ-2546 Third intermediate listing gate

- A third descriptor-relative listing follows the second complete child pass.
- Its set must exactly equal the initially accepted expected-name set.
- The listing occurs while every retained child descriptor remains open.
- No phase callback, receipt parser, or evidence writer runs in between.
- Foreign files and directories are equally invalid root entries.
- Listing failure becomes the existing detail-limited rejection.
