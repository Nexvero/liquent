# LQ-2384 Bound output-target precommit gate

- The private output-parent device and inode are bound before workspace creation and
  rechecked immediately before commit.
- Source workspace and final output must have that same lexical parent.
- Final target absence is checked again relative to the open parent descriptor.
- The source name must resolve without link traversal to the run-bound private
  workspace identity.
- Any failed precommit check leaves the workspace unpublished.
