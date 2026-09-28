# LQ-2451 Bound child-descriptor set contract

- Publication verifies all four phase-output children as one descriptor-held set.
- Path metadata alone cannot substitute for opening each expected directory.
- Every child is opened relative to the already open workspace without following links.
- All descriptors remain open until the complete set has been checked twice.
- Replacement, redirection, metadata drift, or set drift fails closed.
- Descriptor custody remains local evidence and grants no deployment authority.
