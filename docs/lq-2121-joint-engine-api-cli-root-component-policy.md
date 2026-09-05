# LQ-2121 Joint engine API CLI root component policy

- Empty path components are rejected.
- Dot components are rejected.
- Parent components are rejected.
- Repeated separators create invalid empty components.
- No component is normalized away.
- Component order remains caller supplied.
- Root resolution remains authoritative downstream.
