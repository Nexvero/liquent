# LQ-102 — CSRF-Authorized Research Job Start

## Status

- Der bestehende CSRF-Guard und der autorisierte Research-Start sind in einem
  kleinen Anwendungsablauf geordnet.
- CSRF wird vor Membership-Lookup, Resolver, Registrierung und Ausführung
  geprüft.
- Nur nach erfolgreichem Nachweis folgt die bestehende `research:write`-Prüfung.

## Sicherheitsgrenze

Der Ablauf setzt voraus, dass der erwartete CSRF-Wert aus derselben verifizierten
Session wie der Principal stammt. Diese Session-Auflösung ist noch nicht Teil
dieses Slices. Ein ungültiger Nachweis hinterlässt keinen Job und ruft keine
nachgelagerte Komponente auf.

## Bewusst nicht enthalten

- keine Session-Auflösung oder Session-Ablage,
- keine Token-Erzeugung oder Rotation,
- keine Header-, Cookie- oder HTTP-Integration,
- keine Middleware,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

