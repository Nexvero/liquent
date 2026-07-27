# LQ-110 — Browser Session Record Validity

## Status

- Ein unveränderlicher, serverseitiger `BrowserSessionRecord` bindet den
  aufgelösten Kontext an einen eindeutigen Ablaufzeitpunkt und optionalen
  Widerrufszeitpunkt.
- Eine pure Prüfung liefert den Kontext nur vor dem Ablauf und ohne Widerruf.
- Der Ablaufzeitpunkt selbst ist bereits ungültig.
- Alle Zeitwerte müssen zeitzonenbehaftet sein.

## Sicherheitsgrenze

Ein vorhandener Widerrufsmarker führt unabhängig von seinem Zeitwert zum
Fail-Closed-Ergebnis. Die Prüfung liest nur Zustand; sie verlängert oder
verändert keine Session.

## Bewusst nicht enthalten

- kein Session-Lookup-Adapter oder Speicher,
- keine konkrete Lebensdauer oder Idle-Timeout-Regel,
- keine Erzeugung, Rotation oder Widerrufsoperation,
- keine Cookie-Ausgabe oder Login-/Logout-Route,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-111 kann den bestehenden Lookup-Port mit einem kleinen In-Memory-Adapter für
Tests und lokale Ausführung verbinden. Shared Environments bleiben gesperrt.
