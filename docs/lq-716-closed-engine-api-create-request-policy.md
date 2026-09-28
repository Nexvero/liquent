# LQ-716 — Closed Engine API Create Request Policy

## Umsetzung

`ClosedManifestHandoffSupervisorCreateRequestPolicy` validiert einen begrenzten
Createbody vollständig und liefert nur einen typisierten Autorisierungsfakt.

## Kanonizität

UTF-8-JSON wird mit Duplicate-Key-Ablehnung gelesen und muss bytegenau der
sortierten kompakten Rekodierung entsprechen.

Damit existiert keine zweite syntaktische Darstellung desselben Requests.

## Profilbindung

Writer- und Recoverycommand sind fest. Der bestehende Anchorcodec validiert die
14 Argumente; alle sieben Ankerfakten werden erneut gegen Labels und Image
gebunden.

## Mountbindung

Die feste Bindreihenfolge wird syntaktisch zerlegt, ohne Pfade aufzulösen oder
das Dateisystem zu lesen.

Control liegt genau eine Ebene unter seiner Wurzel; Source und Target müssen
lexikalisch innerhalb ihrer getrennten Wurzeln liegen.

## Oberfläche

Es gibt keine Listen-, Connect-, Forward-, Open-, Stat- oder Resolveoperation.
