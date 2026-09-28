# LQ-1392 Final joint engine API acceptance root state gate

- Load supplies its initial root observation to final validation.
- Inspection supplies its inventory-start observation to the same gate.
- Final held and visible facts are evaluated after marker decisions.
- Complete ordered metadata fields must remain byte-for-byte equivalent.
- A mismatch rejects before load or inventory return.
- Descriptor closure executes on success and rejection.
- Record invokes identity validation without an immutable baseline.
