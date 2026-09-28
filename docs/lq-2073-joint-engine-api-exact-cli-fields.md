# LQ-2073 Joint engine API exact CLI fields

- Operation-root field is mandatory.
- Mode field is mandatory.
- No third field is accepted.
- Missing fields cannot default.
- Extra fields cannot influence dispatch.
- Field names are compared as one exact set.
- No reflective fallback exists.
