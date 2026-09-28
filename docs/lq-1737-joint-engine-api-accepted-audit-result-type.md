# LQ-1737 Joint engine API accepted audit result type

- Accepted result contains source and marker observations.
- Source must be the complete run-bound observation type.
- Marker must be the complete acceptance observation type.
- Run authority is decoded only from retained source.
- Expected acceptance is rebuilt from retained envelope.
- Marker acceptance must equal that expected value.
- Representation is redacted.
