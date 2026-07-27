# LQ-101 — CSRF Validation Guard

## Status

- Eine reine, fail-closed Prüfung für mutierende Browseranfragen ist ergänzt.
- Nur ein exakter, nicht leerer CSRF-Nachweis wird akzeptiert.
- Der Vergleich verwendet eine konstante Vergleichsfunktion.
- Ablehnungen liefern ausschließlich `csrf_validation_failed`.

## Sicherheitsgrenze

Erwarteter und übermittelter Wert werden weder gespeichert noch in den Fehler
übernommen. Fehlende, leere und abweichende Werte sind öffentlich nicht
unterscheidbar.

## Bewusst nicht enthalten

- keine Token-Erzeugung oder Rotation,
- kein Session- oder Cookie-Speicher,
- keine Header-/Formularfestlegung,
- keine HTTP-Route oder Middleware,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

Die Route darf erst nach serverseitiger Session-Auflösung und Bindung des
erwarteten CSRF-Nachweises an diese Session abgesichert werden.

