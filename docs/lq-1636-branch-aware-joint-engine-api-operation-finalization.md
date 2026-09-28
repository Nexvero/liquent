# LQ-1636 Branch-aware joint engine API operation finalization

- Wrapper records whether inner work completed successfully.
- Success validates the captured exact snapshot.
- Failure uses existing state-change-aware revalidation.
- Read-only operations retain their original exact path.
- Result propagation occurs only after capture succeeds.
- Final validation remains mandatory in every branch.
- Branch state is internal only.
