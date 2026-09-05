# LQ-2269 compression-runtime preflight evidence

- Runtime phase facts include exact Python and both zlib identities.
- The existing canonical phase digest binds those measured facts.
- Later sdist and wheel phases therefore follow a passed runtime phase.
- Renderer output remains independently compared with candidate bytes.
- No platform path, host name, or mutable environment hint is recorded.
- Bundle evidence schema and publication interfaces remain unchanged.
- The facts are evidence only and confer no release authority.
