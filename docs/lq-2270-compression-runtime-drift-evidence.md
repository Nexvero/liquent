# LQ-2270 compression-runtime drift evidence

- Tests pin Python 3.12.14 and zlib 1.2.12 reviewed constants.
- Tests verify exact compression-runtime facts in isolation.
- Build-version drift is rejected fail closed.
- Loaded-runtime-version drift is independently rejected fail closed.
- Existing tests retain canonical sdist and wheel byte reconstruction.
- No artifact bytes change under the reviewed environment.
- External signing and publication evidence remain open; production_ready=false.
