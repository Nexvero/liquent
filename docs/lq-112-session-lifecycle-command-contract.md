# LQ-112 — Session Lifecycle Command Contract

## Entscheidung

Der schreibende Browser-Session-Lifecycle besteht zunächst aus genau drei
serverseitigen Befehlen: Erzeugen, Rotieren und Widerrufen. Lookup und
Gültigkeitsprüfung bleiben davon getrennte read-only Pfade.

## Erzeugen

- Der Befehl erhält einen bereits verifizierten Principal.
- Session-ID und CSRF-Nachweis werden unabhängig, opak und nicht leer erzeugt.
- Der Ablaufzeitpunkt wird serverseitig aus einer expliziten Policy bestimmt.
- Eine bestehende Session darf nicht überschrieben werden.
- Erst nach erfolgreicher Speicherung darf Cookie-Material ausgegeben werden.

## Rotieren

- Rotation erzeugt eine neue Session-ID und einen neuen CSRF-Nachweis.
- Der alte Eintrag wird im selben atomaren Vorgang unbrauchbar.
- Entweder sind neuer Eintrag und Widerruf des alten Eintrags gemeinsam
  wirksam, oder der Zustand bleibt vollständig unverändert.
- Eine unbekannte oder bereits ungültige Ausgangssession erzeugt keine neue
  Session.

## Widerrufen

- Widerruf macht einen vorhandenen Eintrag dauerhaft unbrauchbar.
- Wiederholter Widerruf desselben Eintrags ist idempotent.
- Eine unbekannte Session erzeugt keinen Eintrag und gibt keine internen
  Details preis.

## Gemeinsame Sicherheitsregeln

- Befehle akzeptieren keine Identität aus Session-ID oder Cookie-Inhalt.
- Zeit und Zufallswerte werden an der äußeren Grenze bereitgestellt und sind
  in Tests kontrollierbar.
- Fehler dürfen keine Session-ID, CSRF-Werte oder Speicherdetails enthalten.
- Nebenläufige Änderungen müssen fail-closed statt per Last-Write-Wins enden.

## Bewusst nicht enthalten

- keine konkrete Lebensdauer, Idle- oder Remember-me-Policy,
- keine Befehls-Ports oder Implementierung,
- keine Datenbanktabellen, Locks oder Transaktionen,
- keine Cookie-Ausgabe oder Login-/Logout-Route,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-113 kann daraus kleine, speicherneutrale Command-Ports und neutrale
Konfliktfehler ableiten. Ein konkreter Store bleibt danach ein eigener Slice.
