# LQ-1965 Joint engine API source authority type gate

- Source observation is validated before field access.
- Authority bytes are read from retained snapshot only.
- Decoder result must have exact authority runtime type.
- Foreign or null authority results fail closed.
- Run identity is obtained only after type validation.
- No decoded value details enter failure text.
- Existing canonical decoder behavior remains unchanged.
