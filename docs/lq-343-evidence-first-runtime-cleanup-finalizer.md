# LQ-343 — Evidence-first Runtime Cleanup Finalizer

## Ergebnis

LQ-343 installiert `liquent-disposable-postgres-cleanup-finalize` als
owner-kontrollierten Finalizer für LQ-341-Reconciliationausgänge.

Er schreibt ausschließlich private Finalization-Evidence und gibt danach den
exakt gebundenen LQ-339-Cleanup-Claim frei. Dockerressourcen bleiben
unverändert.

## Finalisierungsautorisierung

Die neue owner-only Datei bindet geschlossen Finalization-,
Cleanup-Reconciliation- und Cleanup-ID, Run, Phase, Source, Image, Compose,
die vollständige Reconciliationkette sowie alle Evidence- und
Autorisierungshashes.

Der SHA-256 der vollständigen LQ-341-Reconciliation-Autorisierung ist
ausdrücklich enthalten.

Operation muss exakt `finalize_disposable_postgres_runtime_cleanup`, Scope
exakt `runtime_only` und das UTC-Fenster höchstens eine Stunde sein.

Executor und Autorisierer müssen getrennte opaque Identitäten besitzen.
Unbekannte Felder, doppelte Schlüssel, stale Zeit oder Hashabweichung bleiben
detailfrei unavailable.

## Historische Autorität bleibt historisch

Ursprüngliche Cleanup- und LQ-341-Reconciliation-Autorisierung werden nur an
ihrem jeweiligen gültigen historischen Mittelpunkt validiert.

Die aktuelle Finalisierungsautorisierung verlängert weder Inspection- noch
Cleanuprecht.

Run, Cleanup und Projekt müssen weiterhin exakt dieselbe Bindung besitzen.
Caller liefern keinen Zustand, Claimstatus oder gewünschten Ausgang.

## Evidence vor erneuter Inspection

Der Finalizer leitet den Evidencename ausschließlich aus dem vollständigen
SHA-256 der Cleanup-Finalization-ID ab.

Exakt vorhandene owner-only Finalization-Evidence wird vor LQ-341 gelesen und
steuert den idempotenten Retry.

Sie muss regulär, einfach verlinkt, Modus 0600 und vollständig gegen die
aktuelle Autorisierungsbindung validierbar sein.

Widersprüchliche, beschädigte oder fremde Evidence endet unavailable und wird
nicht überschrieben.

## Frische LQ-341-Entscheidung

Ohne Finalization-Evidence führt der Operator LQ-341 unmittelbar mit derselben
historischen Reconciliation-Autorisierung erneut aus.

Der frühere Ausgang wird nicht als CLI-Wert angenommen oder gespeichert.

Die LQ-341-Ausgabe muss kanonische Schema-Version, Operation und einen
geschlossenen Ausgang enthalten. Unbekannter Output bleibt unavailable.

LQ-341 selbst führt ausschließlich read-only Compose-Render, Listen und
Inspects aus.

## Drei finalisierbare Zustände

Die Zuordnung ist geschlossen:

- `runtime_intact` wird `no_effect_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_finalized`;
- `final_evidence_present` wird `cleanup_evidence_confirmed`.

`not_found` wird ohne Write neutral weitergegeben.

`container_stopped`, `container_removed` und
`application_network_removed` ergeben `continuation_required` ohne Evidence-
oder Claimänderung.

`conflict` ergibt `investigation_required` und lässt den Claim ebenfalls
unverändert.

## Getrennte Finalization-Evidence

Der Operator erzeugt keine fehlende LQ-339-Cleanup-Evidence nachträglich.

Stattdessen schreibt er einen getrennten Record, der alle IDs und Hashes,
frisch beobachteten Zustand, neutralen Finalisierungsausgang, getrennte
Identitäten, Finalisierungsautorisierungshash und UTC-Abschluss bindet.

Die Datei wird owner-only per exklusiver Temporäranlage geschrieben,
synchronisiert, atomar final verlinkt und vollständig zurückgelesen.

Erst dieser erfolgreiche Rücklesetest erlaubt Claimfreigabe.

## Exakte Claimfreigabe

Der Claimname stammt ausschließlich aus dem SHA-256 der ursprünglichen
Cleanup-ID.

Ein vorhandener Claim wird vor Freigabe vollständig als kanonischer LQ-339-
Claim gegen dieselbe Run-, Ressourcen-, Identitäts- und Hashbindung geprüft.

Nur der exakte Claim wird einmal entfernt und das Evidenceverzeichnis danach
synchronisiert. Suche, Alter, Prefix- oder Labelauswahl existiert nicht.

Ist der Claim bereits abwesend, ist die Freigabe idempotent abgeschlossen.

## Unbekannte Freigabe und Retry

Schlägt die Claimfreigabe nach persistierter Evidence technisch fehl, bleibt
die Evidence erhalten und der Command unavailable.

Der Retry liest diese Evidence vor LQ-341, prüft nur den exakten Claim und
wiederholt ausschließlich dessen einzelne Freigabe.

Ein fremder oder beschädigter Claim wird nicht entfernt. Der Retry führt
keinen Dockerzugriff und verändert keine Ressource.

## Geschlossene Ausgabe

Die CLI gibt nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_finalization` und einen der LQ-342-
Ausgänge aus.

IDs, Hashes, Pfade, Ressourcen, Zeitwerte und Identitäten bleiben privat.
Technische Nichtverfügbarkeit endet ohne stdout oder stderr.

## Tests

Fake-basierte Tests prüfen alle drei Finalisierungen, alle drei Teilzustände,
Conflict, Not-found und Hashabweichung.

Ein eigener Test erzwingt unbekannte Claimfreigabe nach Evidence und beweist,
dass der Retry ohne Inspector aus derselben Evidence abschließt.

Die CLI-Grenze wird separat geprüft. Kein Test verändert Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 37 Entry Points und 41
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-343 implementiert keine Fortsetzung eines Teilcleanup, keine Dockermutation
und keine Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-344 sollte den streng autorisierten Fortsetzungsvertrag für die drei
eindeutigen Teilzustände definieren.

Er muss pro Ausgang ein minimales verbleibendes Mutationsbudget festlegen und
das erhaltene Datenvolume weiterhin vollständig ausschließen.
