# LQ-536 — Persistent Supervisor Cleanup Retention Policy Authority Recovery

## Ergebnis

LQ-536 implementiert die principalfreie persistente Offline-Recovery der
Retention-Policy-Administrationsauthority.

Recovery ist ausschließlich für einen nachgewiesenen vollständigen effektiven
Lockout und einen historisch bekannten Ziel-User zulässig.

## Principalfreie Grenze

`recover_cleanup_retention_policy_authority` akzeptiert nur den geschlossenen
LQ-531-Recoverycommand.

Die Methode nimmt keinen `SessionPrincipal`, Actor, Allowboolean, Rolle oder
Permission entgegen.

Eine aktive Browser- oder Operatorsession verleiht keine Recoveryauthority.

Die owner-kontrollierte Offline-Prozessgrenze bleibt ein späterer Slice.

## Retry zuerst

Der Adapter sucht die immutable Recovery-ID vor Current-, Lockout-, User-,
Clock- oder Generatorprüfung.

Ein Retry mit identischem Ziel und identischer erwarteter Revision liefert die
historisch resultierende vollständige Set-Revision.

Er erzeugt keine zweite Revision und schaltet keinen aktuellen Pointer erneut.

Abweichende Wiederverwendung derselben Recovery-ID liefert detailfreien
Conflict.

Ein historischer Retry bleibt nach späteren Lifecycleänderungen lesbar, ohne
eine neue Wirkung darzustellen.

## Exakte Erwartung

Die erwartete Set-Revision muss exakt der aktuellen Authorityprojektion
entsprechen.

Fehlende oder stale aktuelle Revision liefert detailfreien Conflict.

Die Erwartung ist kein Wildcard und keine Aufforderung, eine frühere Revision
zu reaktivieren.

## Historisch bekanntes Ziel

Der Ziel-User muss bereits Member der aktuell erwarteten vollständigen
Authoritymenge sein.

Recovery kann keine neue Person grant-en und keine freie User-ID aufnehmen.

Der persistente Ziel-Userfact muss zum Recoveryzeitpunkt weiterhin aktiv sein.

Fehlendes historisches Membership oder inactive Userfact liefert neutral
`None` und keine Wirkung.

Recovery erzeugt oder reaktiviert keinen Userfact.

## Nachgewiesener vollständiger Lockout

Die aktuelle vollständige Menge und alle aktuellen Userfacts werden unter
derselben Transaktion gelesen.

Recovery ist nur zulässig, wenn kein Member zugleich Authoritystatus `active`
und persistierten Userstatus `active` besitzt.

Sobald mindestens ein effektiver Administrator existiert, liefert Recovery
neutral `None`.

Damit ersetzt Recovery keinen regulären LQ-535-Lifecycle.

## Vollständige resultierende Menge

Der Adapter kopiert sämtliche aktuellen Memberfacts in eine neue immutable
Set-Revision.

Nur der historisch bekannte Zielmember wird auf `active` gesetzt.

Alle anderen Memberstatus bleiben unverändert erhalten.

Die neue Revision erhält die nächste positive Sequenznummer.

Die resultierende Revision-ID wird intern erzeugt, typgeprüft und gegen
erwartete sowie bereits persistierte IDs geprüft.

## Atomare Veröffentlichung

Neue Setrevision, vollständige Memberzeilen, erwartungsgebundener Current-
Pointer und immutable Recoveryfact werden in einer Write-Transaktion
gespeichert.

Die vollständigen Memberzeilen entstehen vor der Pointerumschaltung.

Eine verlorene erwartungsgebundene Umschaltung ist technische
Nichtverfügbarkeit und kann keinen partiellen Commit hinterlassen.

Historische Setrevisionen werden nicht verändert.

## Wirkung nach Commit

Der wiederhergestellte Zielmember kann erst nach Commit durch spätere aktuelle
Permit- und Lifecycleauflösung wirksam werden.

Jeder spätere Aufruf liest die neue Current-Revision frisch.

Eine spätere Deaktivierung oder ein inaktiver Userfact sperrt erneut
fail-closed.

Es gibt keinen Recoverycache oder dauerhaften Bypass.

## Zeit und Serialisierung

Die Recoveryclock darf nicht vor der Erzeugungszeit der erwarteten
Authorityrevision liegen.

PostgreSQL sperrt User-, Policy-, Set-, Member-, Current-, Bootstrap-, Change-
und Recoverytabellen in einer festen Reihenfolge.

Lockoutnachweis, Zielprüfung und Pointerwechsel teilen dadurch denselben
serialisierten System-of-Record-Zustand.

SQLite bleibt lokale Testgrenze.

## Fehlergrenzen

Vorhandene effektive Authority sowie fehlendes oder inaktives historisches Ziel
liefern neutral `None`.

Stale Erwartung, abweichender Retry und Revision-ID-Kollision liefern den
bestehenden feldlosen Conflict.

Beschädigte Persistenz, regressierende Clock, Generator-, Dialekt- oder
Infrastrukturfehler bleiben detailfreie
`ManifestHandoffRegistryUnavailable`.

LQ-536 führt keinen neuen Exceptiontyp ein.

## Bewusst nicht enthalten

Keine neue Person, kein Bootstrap und kein regulärer Lifecycle.

Keine Policyänderung, Ausnahmeverkürzung oder Evaluation.

Keine Cleanup-, Datei- oder Operatorwirkung.

Keine Migration, CLI, Route, Composition, Konfiguration oder Productionwiring.

## Bestand

Der Bestand bleibt bei 63 Entry Points, 68 Operatormodulen und 42 linearen
Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-537 definiert die owner-kontrollierten Operatorgrenzen für Bootstrap,
reguläre Policyadministration, Authority-Lifecycle und Offline-Recovery.
