# LQ-672 — Installable Manifest Capability Primitives

## Ergebnis

Die drei bestehenden Implementierungen wurden ohne Algorithmuskopie nach
`src/liquent_platform/capabilities` verschoben.

## Renderer

`pre_staging_manifest` behält deterministischen Doppelsnapshot,
Git-Bestandsgrenze, Dateideskriptorprüfung, kanonische Bytes und geschlossene
Reviewzuordnung unverändert bei.

## Writer

`private_manifest_handoff` behält sichere Directoryauflösung, exklusiven
temporären Write, fsync, no-overwrite Hardlink-Bindung und
Unknown-after-possible-link unverändert bei.

Der Rendererimport zeigt jetzt ausschließlich auf den package-lokalen Namespace.

## Reconciler

`private_manifest_handoff_reconcile` behält seine ausschließlich read-only
Beobachtung und die bestehenden sechs geschlossenen Outcomes bei.

Gemeinsame Validierungshilfen stammen ausschließlich aus dem package-lokalen
Writer.

## Anwendung

Die bestehende persistente Manifest-Handoff-Anwendung importiert Writer und
Reconciler nun aus `liquent_platform.capabilities` statt aus `tools`.

## Kompatibilität

Die drei bisherigen Tooldateien enthalten nur CLI-Weiterleitung und
`sys.modules`-Alias auf die jeweilige package-lokale Implementierung.

Direkter Toolimport und package-lokaler Import sind daher objektidentisch.
