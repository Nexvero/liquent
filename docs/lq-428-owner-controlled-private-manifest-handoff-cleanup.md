# LQ-428 — Owner-Controlled Private Manifest Handoff Cleanup

## Zweck

LQ-428 implementiert den eng begrenzten Cleanup eines redundanten temporären
Namens nach einem privaten Manifest-Handoff.

Nur der erneut und lokal belegte Zustand
`manifest_handed_off_pending_cleanup` ist mutierbar.

## Lokale Moduloberfläche

Der bewusste Aufruf lautet:

```text
python -m tools.private_manifest_handoff_cleanup \
  --target-root PRIVATE_0700_DIRECTORY \
  --handoff-name EXISTING_NAME
```

Es wird kein Console Entry Point installiert und nichts automatisch
verdrahtet.

## Autoritative Eingaben

Der Caller liefert ausschließlich die bestehende private Zielwurzel und den
begrenzten Handoffnamen.

Nicht akzeptiert werden Tempname, Digest, Dateizahl, Inode, Reconciliation-
Ergebnis, Erfolgsboolean oder Löschfreigabe.

Alle entscheidenden Fakten werden aus dem owner-kontrollierten Systemzustand
abgeleitet.

## Zielgrenze

Die Zielwurzel muss weiterhin owner-eigen, komponentenweise symlinkfrei und
exakt `0700` sein.

Der Cleanup öffnet sie zusätzlich als Directory-Descriptor mit
`O_NOFOLLOW` und bindet Device, Inode, Owner und Modus erneut.

Interne absolute Pfade werden nicht ausgegeben.

## Erforderlicher Ausgangszustand

Der bestehende read-only Reconciler muss unmittelbar
`manifest_handed_off_pending_cleanup` feststellen.

Danach werden Final und genau ein passender Writer-Tempname erneut aus dem
Zielverzeichnis ermittelt und über den Directory-Descriptor geöffnet.

Eine frühere Reconciliation oder caller-gelieferte Behauptung genügt nicht.

## Erneute Bindungsprüfung

Beide Namen müssen owner-eigene reguläre Dateien mit Modus `0600` sein.

Beide Inhalte müssen dasselbe kanonische Manifest Schema 1 mit allen vier
Nichtautorisierungsflags bilden.

Final und Temp müssen bei geöffneten Deskriptoren sowie unmittelbar vor der
Mutation dasselbe Device und denselben Inode besitzen.

Digest und Dateizahl müssen übereinstimmen und werden nur aus gelesenen Bytes
abgeleitet.

## Einzige Mutation

Nach vollständig erfolgreicher Revalidierung entfernt der Cleanup exakt den
ermittelten temporären Verzeichnisnamen.

Er löscht, ersetzt, benennt oder verändert die finale Manifestdatei nicht.

Er erzeugt keinen neuen Namen und verändert weder Inhalt, Modus noch Owner.

## Dauerhaftigkeit und Abschluss

Nach Entfernung des Tempnamens wird der Zielverzeichnis-Descriptor mit
`fsync` synchronisiert.

Der finale Name muss danach weiterhin auf den zuvor belegten Device-/Inode-
Zustand zeigen.

Es darf kein passender Tempname verbleiben.

Dann lautet der Ausgang `manifest_handoff_cleanup_completed`.

Er enthält nur finalen Dateinamen, Digest und Dateizahl sowie die beiden
Nichtautorisierungsflags für Staging und Commit.

## Nicht anwendbare Zustände

Abwesenheit, vollständiger Erfolg ohne Tempname, Temporary-only und Konflikt
ergeben `cleanup_not_applicable` mit dem aktuell beobachteten Ausgang.

Sie verändern keine Datei und autorisieren keine Namenswiederverwendung.

Ein Drift zwischen erster Klassifikation und Revalidierung ergibt
`manifest_handoff_cleanup_conflict` ohne Mutation.

## Technische Unverfügbarkeit

Zugriffs-, Open-, Read- oder Metadatenfehler vor möglicher Entfernung werden
detailfrei als `manifest_handoff_cleanup_unavailable` mit Exitcode 2
vereinheitlicht.

Interne Betriebssystemdetails werden nicht ausgegeben.

## Unbekannter Ausgang

Jeder technische Fehler nach möglicher Entfernung des Tempnamens ergibt
detailfrei `manifest_handoff_cleanup_outcome_unknown` mit Exitcode 4.

Es erfolgt kein Retry, keine zweite Löschung und keine weitere Mutation.

Der Zustand muss danach erneut read-only reconciled werden.

## Exitcodes

- 0 nur für belegten und dauerhaft abgeschlossenen Cleanup;
- 3 für nicht anwendbare oder konfliktbehaftete Zustände;
- 2 für technische Unverfügbarkeit vor möglicher Mutation;
- 4 für unbekannten Ausgang nach möglicher Mutation.

Kein Exitcode autorisiert Staging, Commit oder andere Releaseaktionen.

## Namensretention

Der finale Handoffname bleibt belegt und wird nicht freigegeben.

Weder Cleanup-Erfolg noch spätere Abwesenheit eines Tempnamens erlauben die
Wiederverwendung des Handoffnamens.

Eine persistente Attempt-Registry wird in diesem Slice nicht eingeführt.

## Tests

Die Tests belegen:

- Entfernung ausschließlich des redundant verlinkten Tempnamens;
- unveränderten finalen Inode und unveränderte Manifestbytes;
- keine Mutation bei Abwesenheit, Temporary-only, vollständigem Erfolg oder
  Konflikt;
- erneute Revalidierung unmittelbar vor der Mutation;
- unbekannten Ausgang bei Fehler nach Entfernung und Erhalt der Finaldatei;
- fehlende Installation als Console Entry Point.

## Ausführungsgrenze

LQ-428 verwendet ausschließlich synthetische private Testverzeichnisse.

Der Cleanup wird nicht gegen einen echten Handoff oder den kumulierten
Worktree ausgeführt.

## Nichtziele

LQ-428 implementiert keine Retentionlöschung der finalen Evidenz, keine
Attempt-Registry, Wiederverwendung, Discovery, Batchverarbeitung oder
automatische Recovery.

Der Slice staged, committed, pusht, baut, signiert, promotet, publiziert oder
deployed nichts.

## Nächster Slice

LQ-429 sollte den read-only Abschlussaudit für Writer, Reconciliation und
Cleanup sowie die verbleibende Retention- und Attempt-Registry-Lücke
dokumentieren.
