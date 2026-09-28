# LQ-2048 Joint engine API silent argument parser

- One private parser owns CLI parse failures.
- Parser error raises existing unavailable failure.
- Parser exit raises existing unavailable failure.
- Neither path prints a message.
- Parser construction occurs inside main handling.
- No help action is introduced.
- No public parser API is added.
