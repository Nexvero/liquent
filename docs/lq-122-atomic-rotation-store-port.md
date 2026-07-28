# LQ-122 — Atomic Rotation Store Port

## Ergebnis

Ein speicherneutraler `BrowserSessionRotationStore`-Port beschreibt genau eine
atomare Operation: einen gültigen bestehenden Session-Eintrag widerrufen und im
selben Schritt den Ersatz-Eintrag anlegen. Der Port ergänzt den vorhandenen
`BrowserSessionCreationStore` und bleibt wie dieser adapter- und
speicherneutral.

## Verhalten

- `rotate_session` erhält die aktuelle Session-ID und das neue
  `IssuedBrowserSession`-Material (Ersatz-Session-ID, CSRF-Nachweis, Ablauf).
- Der Store liest den bestehenden Record selbst, übernimmt dessen **unveränderten
  Principal** für den Replacement-Record, widerruft den alten Eintrag und legt
  den neuen Eintrag an — alles in einem atomaren Schritt.
- Erfolg (`True`) bedeutet: der alte Eintrag ist danach unbrauchbar und der neue
  Eintrag ist angelegt — beides gemeinsam. Es gibt keinen Zustand, in dem alte
  und neue Session gleichzeitig aktiv bleiben.
- Eine unbekannte oder nicht mehr gültige (abgelaufene oder widerrufene)
  Ausgangssession liefert neutral `False` und legt keinen neuen Eintrag an.
- Eine bereits vergebene Ziel-ID liefert `False` und überschreibt keinen Record.
- Der Rückgabewert ist ausschließlich ein `bool`; es werden keine IDs, Records
  oder internen Bestandsinformationen nach außen getragen.

## Principal-Bindung

Der Aufrufer übergibt **keinen** Principal. Da der Store den Principal
ausschließlich aus dem bestehenden Record der Ausgangssession übernimmt, kann ein
Replacement-Record konstruktiv keinen fremden Principal binden. Der Port trägt
daher weder ein Principal- noch ein vollständig gebautes Record-Argument.

## Zeit und Zufall

Die Gültigkeits- und Widerrufszeit stammt aus der im Adapter injizierten Uhr —
identisch zu `BrowserSessionLookup` und `BrowserSessionCreationStore`. Der Port
trägt daher bewusst keinen Zeit- oder Zufallsparameter. Ersatz-Session-ID,
CSRF-Nachweis und Ablauf werden außerhalb erzeugt und als `IssuedBrowserSession`
übergeben.

## Bewusst nicht enthalten

- keine Rotation-Implementierung oder Schreiblogik (In-Memory-Adapter: LQ-124),
- kein Rotate-Anwendungsfall (LQ-123),
- keine Uhr-, Zufalls- oder Lebensdauer-Policy,
- keine Datenbank, Locks oder Transaktionen,
- keine HTTP-, Cookie- oder Login-/Logout-Integration,
- keine CORS-, Provider- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-123 kann den Rotate-Anwendungsfall über diesen Port und den vorhandenen
sicheren Materialgenerator spezifizieren; Laufzeit und Uhr werden dort explizit
injiziert. Ein konkreter atomarer Rotations-Adapter bleibt LQ-124.
