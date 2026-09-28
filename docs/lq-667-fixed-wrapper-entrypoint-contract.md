# LQ-667 — Fixed Wrapper Entrypoint Contract

## Ergebnis

Writer und Recovery benötigen zwei feste installierbare Entrypoints, die jeweils
genau ein Profil ausführen und keine freie Command- oder Importwahl zulassen.

Dieser Slice definiert den Vertrag, aktiviert die Entrypoints aber noch nicht.

## Eingabe

Die einzige variable Prozesseingabe ist die vollständige kanonische
LQ-660-Ankerfolge nach dem festen process-eigenen Command.

Fehlende, zusätzliche, umsortierte oder profilfremde Argumente scheitern vor
Launchdatei-, Gate- oder Capabilitywirkung.

Environment, Arbeitsverzeichnis, Modulname und Requestcommand sind keine
Konfigurationsquelle.

## Feste Containerpfade

Launch wird ausschließlich aus
`/run/liquent/launch/launch-binding.json` gelesen.

Gate- und Terminalartefakte liegen ausschließlich unter
`/run/liquent/control`.

Writer arbeitet ausschließlich mit `/run/liquent/source` und
`/run/liquent/target`; Recovery ausschließlich mit `/run/liquent/target`.

## Ablauf

Jeder Entrypoint decodiert den externen Anker, lädt das exakt gebundene
Launchdokument und komponiert genau einen LQ-628-Kindprozess.

Danach gilt Ready → bounded Release-Wait → Consumed → genau eine
Capabilitywirkung → Terminal.

Ein Entrypoint führt keinen Retry und keinen zweiten Prozess aus.

## Capabilitygrenze

Writer muss den bestehenden privaten Manifest-Handoff als package-lokale
Primitive ausführen.

Recovery muss ausschließlich die bestehende read-only Reconciliation als
package-lokale Primitive ausführen.

Shell, subprocess, dynamischer Import und Aufruf eines `tools/`-Skripts sind
unzulässig.

## Fehlergrenze

Neutraler Gatekonflikt und technische Unverfügbarkeit bleiben detailfrei.

Der Prozess gibt weder IDs, Pfade, Digests noch Artefaktinhalte aus.

## Keine Authority

Der Wrapper entscheidet keine Admission, Membership, Rolle oder Permission.

SessionPrincipal und caller-gelieferte Allowwerte sind nicht Teil der
Composition.
