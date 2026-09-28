# LQ-535 — Persistent Supervisor Cleanup Retention Policy Authority Lifecycle

## Ergebnis

LQ-535 implementiert den regulären erwartungsgebundenen Lifecycle der
separaten Retention-Policy-Administrationsauthority.

Jede Änderung erzeugt eine neue vollständige immutable Authority-Set-Revision
und veröffentlicht sie atomar als aktuelle Projektion.

Offline-Recovery bleibt getrennt.

## Geschlossene Lifecyclegrenze

Die bestehende Methode
`change_cleanup_retention_policy_authority` akzeptiert ausschließlich einen
echten `SessionPrincipal` und den geschlossenen LQ-531-Command.

Zulässig sind nur `grant`, `deactivate` und `reactivate`.

Der Caller liefert keine resultierende Revision, vollständige Membermenge,
Rolle, Permission oder Allowbehauptung.

## Retry zuerst

Die immutable Change-ID wird vor aktueller Authority, Userstatus, Clock und
Revisiongenerator aufgelöst.

Ein in Actor, Ziel, erwarteter Revision und Intent identischer Retry liefert
die historisch resultierende vollständige Set-Revision.

Er verändert die aktuelle Projektion nicht und verlangt keine heute noch
bestehende Authority.

Abweichende Wiederverwendung derselben ID liefert detailfreien Conflict.

## Exakte Erwartung

Die Commandrevision muss exakt der aktuellen Authority-Set-Revision
entsprechen.

Fehlende aktuelle Authority oder eine stale Revision liefert detailfreien
Conflict.

Die Expected-Revision ist niemals Wildcard.

## Actor und Ziel aus dem System of Record

Der Actor muss aktiver Member der aktuellen vollständigen Menge sein.

Actor und Ziel müssen außerdem als aktive persistente Userfacts existieren.

Ein `SessionPrincipal` allein erteilt keine Lifecycleauthority.

Inactive oder fehlende Userfacts wirken fail-closed und erzeugen keine neue
Revision.

Ordinary Membership, Researchpermissions und Cleanup-Source-Authorities werden
nicht konsultiert und nicht verändert.

## Transitionen

`grant` ist nur für einen bisher nicht vorhandenen Ziel-User zulässig.

`deactivate` ist nur für einen aktuell aktiven Member zulässig.

`reactivate` ist nur für einen aktuell inaktiven Member zulässig.

No-op, Doppelgrant und unpassende Statuswechsel liefern detailfreien Conflict.

## Vollständige neue Menge

Der Adapter kopiert sämtliche bisherigen Memberfacts in eine neue Revision und
ändert darin ausschließlich den Zielstatus.

Die neue Revision erhält die nächste positive Sequenznummer.

Alle Memberzeilen werden vor Umschaltung der aktuellen Projektion geschrieben.

Historische Revisionen und Member werden niemals überschrieben.

Die neue Revision-ID wird intern erzeugt, typgeprüft und darf weder der
erwarteten noch einer bereits vorhandenen Revision entsprechen.

## Lockoutschutz

Vor Persistenz muss in der resultierenden Menge mindestens ein aktiver Member
mit weiterhin aktivem Userfact verbleiben.

Die Deaktivierung des letzten effektiven Administrators wird detailfrei
abgelehnt.

Ein nur formal aktiver, aber persistiert inaktiver User verhindert Lockout
nicht.

Offline-Recovery bleibt für bereits extern entstandene Lockoutzustände der
nächste getrennte Mechanismus.

## Atomare Veröffentlichung

Setrevision, vollständige Membermenge, Current-Pointer und immutable
Authority-Changefact werden unter einer Write-Transaktion gespeichert.

Der Pointer wird erwartungsgebunden von der alten auf die neue Revision
umgeschaltet.

Eine unerwartet verlorene Umschaltung ist technische Nichtverfügbarkeit und
kann keinen partiellen Commit hinterlassen.

## Widerruf

Nach Commit sieht jeder spätere Permit- oder Lifecycleaufruf die neue aktuelle
Menge.

Ein deaktivierter Member kann keine spätere neue Policymutation oder
Authoritymutation autorisieren.

Historische Retry-Auflösung bleibt davon getrennt und erzeugt keine Wirkung.

## Zeit und Serialisierung

Die Clock darf nicht vor der Erzeugungszeit der erwarteten Set-Revision liegen.

PostgreSQL sperrt User-, Policy-, Set-, Member-, Current-, Bootstrap-, Policy-
und Authority-Changetabellen in fester Reihenfolge.

Actor-, Ziel-, Erwartungs- und Lockoutprüfung teilen dadurch denselben
serialisierten System-of-Record-Zustand.

SQLite bleibt lokale Testgrenze.

## Fehlergrenzen

Fehlende effektive Actor- oder Targetfacts liefern neutral `None`.

Stale Revision, ungültige Transition, Lockout, ID-Kollision oder abweichender
Retry liefern den bestehenden feldlosen Conflict.

Beschädigte Persistenz, regressierende Clock, Generator-, Dialekt- oder
Infrastrukturfehler bleiben detailfreie
`ManifestHandoffRegistryUnavailable`.

Kein neuer Exceptiontyp wird eingeführt.

## Bewusst nicht enthalten

Keine Offline-Recovery und keine automatische Ersatzperson.

Keine Policyverkürzung oder Änderung der LQ-534-Policysemantik.

Keine Evaluation, Cleanupwirkung, Migration, CLI, Route, Composition,
Konfiguration oder Productionwiring.

## Bestand

Der Bestand bleibt bei 63 Entry Points, 68 Operatormodulen und 42 linearen
Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-536 implementiert die geschlossene persistente Offline-Recovery für einen
nachgewiesenen Authority-Lockout mit historisch bekanntem Ziel-User.
