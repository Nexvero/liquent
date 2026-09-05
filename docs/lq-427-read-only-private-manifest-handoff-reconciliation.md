# LQ-427 — Read-Only Private Manifest Handoff Reconciliation

## Zweck

LQ-427 implementiert die ausschließlich read-only Reconciliation eines
privaten LQ-426-Manifest-Handoffs.

Sie klassifiziert Final- und Tempzustände nach Erfolg, Abwesenheit,
Cleanupbedarf, Konflikt oder technischer Unverfügbarkeit.

## Aufruf

```text
python -m tools.private_manifest_handoff_reconcile \
  --target-root PRIVATE_0700_DIRECTORY \
  --handoff-name EXISTING_NAME
```

Die Oberfläche wird nicht als Console Entry Point installiert.

## Vertrauensgrenze

Zielwurzel und Name folgen denselben Owner-, Modus-, Symlink- und
Zeichengrenzen wie der Writer.

Die Reconciliation erhält keinen erwarteten Digest, Filecount, Erfolgsboolean
oder Tempnamen vom Caller.

Passende Tempnamen werden ausschließlich aus dem Writerformat
`.NAME-RANDOM.tmp` ermittelt.

## Read-only Beobachtung

Final- und Tempdateien werden mit `lstat` und `O_NOFOLLOW` beobachtet.

Akzeptiert werden nur owner-eigene reguläre Dateien mit Modus `0600`.

Manifestbytes müssen kanonisches Schema 1 mit allen vier
Nichtautorisierungsflags bilden.

Digest und Dateizahl werden nur aus den beobachteten Bytes abgeleitet.

## Abwesenheit

Fehlen finaler und passender temporärer Name, lautet der neutrale Ausgang
`manifest_absent`.

Abwesenheit autorisiert keine Wiederverwendung des Namens, weil keine
persistente Attempt-Registry existiert.

## Vollständiger Erfolg

Eine valide finale Datei ohne passenden Tempnamen ergibt
`manifest_handed_off`.

Der Ausgang enthält nur finalen Dateinamen, Digest und Dateizahl.

Er autorisiert weder Staging noch Commit.

## Temporärdatei ohne Final

Eine valide einzelne Tempdatei ohne Final ergibt `manifest_temporary_only`.

Dieser Zustand kann vor Bindung oder nach einem unbekannten Abbruch entstanden
sein.

Die Reconciliation bindet, löscht oder benennt die Tempdatei nicht um.

## Erfolg mit Cleanupbedarf

Sind Final- und genau eine Tempdatei valide und verweisen sie auf denselben
Device-/Inodezustand mit identischen Manifestfakten, lautet der Ausgang
`manifest_handed_off_pending_cleanup`.

Damit ist der Bindeeffekt beobachtet, aber die Entfernung des temporären Namens
noch nicht abgeschlossen.

LQ-427 entfernt den Namen nicht.

## Konflikt

`manifest_handoff_conflict` gilt insbesondere bei:

- symbolischem oder nicht regulärem Final;
- falschem Owner oder Modus;
- nicht kanonischem Manifest;
- mehr als einer passenden Tempdatei;
- ungültiger Tempdatei;
- unterschiedlichen Inodes oder Fakten von Final und Temp.

Konflikt ist kein technischer Fehler und kein Erfolg.

Er erfordert Owneruntersuchung und erlaubt keine Mutation.

## Technische Unverfügbarkeit

Fehler beim Zugriff auf Zielwurzel, Directorylisting, Open, Read oder
Metadatenbeobachtung enden detailfrei als
`manifest_handoff_reconciliation_unavailable` mit Exitcode 2.

Interne Pfade und Betriebssystemdetails werden nicht ausgegeben.

## Exitcodes

- 0 nur für `manifest_handed_off` ohne Cleanupbedarf;
- 3 für Abwesenheit, Temporary-only, Pending-cleanup und Konflikt;
- 2 für technische Unverfügbarkeit.

Kein Exitcode autorisiert Git- oder Releaseaktionen.

## Keine Mutation

Der Reconciler:

- schreibt keine Datei;
- ändert keinen Modus oder Owner;
- erzeugt keinen Link;
- entfernt keinen Temp- oder Finalnamen;
- reserviert keinen Namen;
- verändert weder Gitindex noch Sourcebaum.

## Tests

Die Tests belegen:

- Abwesenheit und vollständigen Erfolg;
- Temporary-only;
- per Hard-Link beobachteten Pending-cleanup-Erfolg;
- Symlink- und Mehrfachtempkonflikt;
- unterschiedliche Final-/Temp-Inodes;
- unveränderte Datei-Inodes und Bytes nach Beobachtung;
- fehlende Entry-Point-Installation.

## Ausführungsgrenze

LQ-427 reconciled nur synthetische private Testverzeichnisse.

Es existiert weiterhin kein persistentes Manifest für den echten kumulierten
Worktree.

## Nichtziele

LQ-427 implementiert keinen Cleanup, Retry, Rebind, Retentiondeleter oder
persistenten Attempt-Store.

Der Slice staged, committed, pusht, baut, signiert, promotet, publiziert oder
deployed nichts.

## Nächster Slice

LQ-428 sollte den owner-kontrollierten Cleanupvertrag für den ausschließlich
belegten Zustand `manifest_handed_off_pending_cleanup` definieren.

Abwesenheit, Temporary-only und Konflikt dürfen dadurch nicht mutierbar werden.
