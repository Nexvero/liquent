# LQ-115 — Browser Session Issuance

## Status

- Ein eigener Generator-Port liefert unabhängig eine opake Session-ID und
  einen CSRF-Nachweis.
- Der Issuance-Anwendungsfall berechnet aus expliziter Zeit und positiver
  Laufzeit genau einen Ablaufzeitpunkt.
- Das erzeugte Material fließt in den bestehenden atomaren Create-Pfad.
- Ungültige Laufzeiten oder leere Generatorwerte erreichen den Store nicht.

## Sicherheitsgrenze

Der Port ist der Vertrag für eine kryptographisch geeignete äußere Quelle. Die
Anwendung leitet Session-ID und CSRF-Wert nicht voneinander ab. Eine Kollision
wird weiterhin neutral und ohne automatischen stillen Retry gemeldet.

## Bewusst nicht enthalten

- kein konkreter Zufallsgenerator und keine Entropiegröße,
- keine globale Lebensdauer- oder Remember-me-Policy,
- kein konkreter Store oder Datenbankschema,
- keine Rotation, Widerrufs-, HTTP-, Cookie- oder Login-Integration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-116 kann einen kleinen Standardgenerator mit expliziter Mindestentropie
bereitstellen. Production-Wiring bleibt ein eigener späterer Slice.
