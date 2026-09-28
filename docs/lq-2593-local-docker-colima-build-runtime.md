# LQ-2593 Local Docker and Colima build runtime

- Homebrew installed Docker CLI 29.8.0, Colima 0.10.3, and Grype 0.118.0.
- Colima provides a local ARM64 Docker 29.5.2 engine.
- The VM is limited to two CPUs, four GiB memory, and twenty GiB disk.
- No daemon socket, image, credential, or registry access is exposed by Liquent.
- The Docker context remains local and no registry login was performed.
- No image was pushed, signed, published, or deployed.
- Tool installation is host state rather than repository release evidence.
- CI still owns its independently pinned tool versions.
