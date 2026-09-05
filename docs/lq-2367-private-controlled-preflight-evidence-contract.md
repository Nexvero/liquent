# LQ-2367 Private controlled-preflight evidence contract

- Final controlled-preflight evidence is created only inside the still-private
  mode-0700 orchestration workspace.
- The workspace is opened as a directory without symbolic-link traversal.
- Evidence has the fixed name `controlled-preflight.json`; callers cannot choose an
  alternate name or path.
- Empty evidence and non-private workspaces fail closed.
- The evidence explicitly grants no publishing or deployment authority.
