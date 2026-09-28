# LQ-659 — Immutable Child Launch Anchor Contract

## Ergebnis

Ein Supervisor-Kindprozess erhält seine vollständige externe
Launchdokument-Erwartung als feste, geordnete Prozessargumente.

Diese Argumente werden ausschließlich aus den bereits validierten
systemeigenen Container-Create-Fakten konstruiert.

## Vollständige Bindung

Der Anker enthält Dokument-ID, kanonischen SHA-256, Creation-ID, Handle-ID,
Control-Directory-ID, Image-Digest und Writer-/Recovery-Profil.

Kein Teil darf aus dem zu prüfenden Launchdokument ergänzt oder geraten werden.

## Geschlossene Argumentmenge

Flaggen, Reihenfolge und Anzahl sind fest. Fehlende, zusätzliche, umsortierte,
leere, überlange oder technisch unsichere Werte scheitern geschlossen.

Es gibt kein allgemeines Argumentmapping, keine freien Optionen und kein
Environment-Fallback.

## Keine Authority

Der Anker korreliert genau einen Container mit genau einem Launchdokument.

Er enthält kein Allowboolean, keine Rolle, Membership, Researchpermission oder
sonstige Authority und kann keine Capability freigeben.

## Beobachtung

Containeradoption verlangt neben Labels, Image und Sicherheitsprofil dieselbe
vollständige feste Entrypointfolge.

Ein intern divergenter Container ist technisch unverfügbar; ein intern
konsistenter, aber vom Parent-Sollanker abweichender Container bleibt der
bestehende neutrale Reconciliationkonflikt.

## Grenzen

Der Slice öffnet keinen Wrapper-Entrypoint, Mount, Settings-, Appfactory-,
Compose-, Schema-, SQL-, Migrations- oder Productionpfad.
