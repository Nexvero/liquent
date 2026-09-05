# LQ-2504 Intermediate identity-map verifier

- The verifier accepts the controller-held name-to-identity mapping directly.
- Expected names must remain a subset of the four fixed phase outputs.
- Root identity, exact entry set, private mode, and owner remain mandatory.
- Each child is inspected relatively without following symbolic links.
- Its device and inode must equal the corresponding captured identity.
- A stable second listing closes every successful verification pass.
