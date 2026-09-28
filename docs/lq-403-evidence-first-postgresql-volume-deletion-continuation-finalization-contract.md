# LQ-403 — Evidence-first PostgreSQL Volume Deletion Continuation Finalization Contract

## Zweck

LQ-403 definiert die kontrollierte Finalisierung eindeutig beobachteter
LQ-402-Volume-Deletion-Continuation-Zustände.

Der spätere Finalizer persistiert eigene private Evidence vor möglicher
Freigabe des exakten LQ-400-Unterclaims.

Dieser Slice implementiert keinen Command, Evidencewriter, Claimrelease,
Dockerzugriff oder Ressourceneffekt.

## Separate Finalization-Authority

Lösch-, Reconciliation-, Finalisierungs-, Continuation- und
Continuation-Reconciliation-Autorisierung gewähren kein Recht zur
Continuation-Finalisierung.

Ein späterer Finalizer benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer
Volume-Deletion-Continuation-Finalization-ID.

Sie muss mindestens geschlossen binden:

- Continuation-Finalization- und Continuation-Reconciliation-ID;
- Continuation-, Continuation-Claim- und ursprüngliche Claim-ID;
- ursprüngliche Finalization-, Reconciliation-, Volume-Deletion- und
  Volume-Disposition-ID;
- Retention-, Legal-Hold- und Recoveryentscheidungs-IDs;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- SHA-256 der Continuation-Reconciliation-, Continuation-, Finalisierungs-,
  Reconciliation-, Lösch- und Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- Operation exakt
  `finalize_disposable_postgres_volume_deletion_continuation`;
- Scope exakt `data_volume_only`;
- neue getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder beobachteten Zustand, Claimstatus, Zielausgang,
Volumename, Rolle noch Allow-Boolean.

## Keine neue Ressourcenauthority

Die Finalization-Authority erlaubt ausschließlich eigene Evidence und die
spätere Freigabe genau des gebundenen LQ-400-Unterclaims.

Sie verlängert keine frühere Authority und erlaubt keinen weiteren
Volume-Remove.

SessionPrincipal, Membership, Researchpermission, Rollenname und Besitz des
Prozesskontos gewähren kein Finalisierungsrecht.

Der Actor identifiziert den Finalizer, autorisiert aber allein weder Write
noch Entscheidung.

Deaktivierung, Widerruf, Fehlen oder widersprüchliche Bindung stoppt
fail-closed.

## Vollständige historische Bindung

Der Finalizer validiert Resolver-, Lösch-, Reconciliation-, ursprüngliche
Finalisierungs-, Continuation- und Continuation-Reconciliation-Autorisierung
sowie Lineage-, Retention-, Hold- und Recoveryartefakte erneut.

Historische Autorisierungen werden nur in ihrem damaligen gültigen Kontext
strukturell geprüft.

Die aktuelle Continuation-Finalization-Authority muss aktuell sein und den
bytegenauen SHA-256 der vollständigen LQ-402-Autorisierung binden.

IDs, Run, Source, Image, Compose, Volume, Operation, Scope, Identitäten und
sämtliche Hashbeziehungen müssen exakt übereinstimmen.

Neue Finalization-Authority repariert keine beschädigte historische Evidence
und verlängert kein früheres Zeitfenster.

## Getrennte Finalisierungsidentitäten

Finalization-Executor, -Authorizer und -Reviewer müssen drei verschiedene
aktive Identitäten sein.

Sie bleiben von allen bereits gebundenen Resolver-, Clearance-, Lösch-,
Reconciliation-, ursprünglichen Finalisierungs-, Continuation- und
Continuation-Reconciliation-Identitäten getrennt.

Identitätsüberschneidung, Inaktivität oder widersprüchliche Zuordnung stoppt
vor Evidence, Claimprüfung und Docker.

## Finalization-Evidence vor Inspector

Der private Finalization-Evidencepfad wird ausschließlich aus dem
vollständigen SHA-256 der stabilen
Volume-Deletion-Continuation-Finalization-ID abgeleitet.

Vor LQ-402 und vor jedem Dockerzugriff wird dort vorhandene Evidence
vollständig geprüft.

Exakt gebundene Evidence steuert ausschließlich den idempotenten Retry der
Freigabe des untergeordneten LQ-400-Claims.

Malformed, teilweise, fremde oder anders gebundene Evidence ist technische
Nichtverfügbarkeit und wird weder überschrieben noch ignoriert.

Ohne Finalization-Evidence beginnt der normale Weg mit einer frischen
LQ-402-Entscheidung.

## Frische LQ-402-Entscheidung

Der Finalizer führt den LQ-402-Inspector unmittelbar vor jeder neuen
Evidenceanlage mit denselben autoritativen Inputs erneut aus.

Gespeicherter stdout, Tickettext, caller-gelieferter Zustand oder früheres
Ergebnisobjekt genügt nicht.

Die Ausgabe muss kanonische Schemaversion, feste Reconciliationoperation und
einen geschlossenen LQ-402-Ausgang besitzen.

Unbekannter oder malformed Output ist technische Nichtverfügbarkeit.

LQ-402 bleibt strikt read-only und darf Docker nur gemäß seiner exakten
Beobachtungsgrenze lesen.

## Ursprünglicher Claim bleibt Voraussetzung

Vor jeder neuen Finalization-Evidence muss der ursprüngliche LQ-394-Claim
offen, kanonisch und exakt an dieselbe historische Kette gebunden sein.

Seine lesbare Abwesenheit wird `investigation_required`, weil LQ-403 den
übergeordneten Löschlebenszyklus nicht isoliert abschließen darf.

Beschädigung oder Fremdbindung bleibt technische Nichtverfügbarkeit.

Der ursprüngliche Claim wird durch LQ-403 niemals freigegeben oder verändert.

## Terminal finalisierbare Zustände

Nur zwei frisch beobachtete Zustände sind terminal finalisierbar:

- `continuation_evidence_present` wird
  `continuation_evidence_confirmed`;
- `volume_absent_evidence_missing` wird
  `volume_removal_ready_for_deletion_finalization`.

Beide erlauben eigene Finalization-Evidence und danach die Freigabe
ausschließlich des exakten LQ-400-Unterclaims.

Sie betreffen nur das exakte lokale Docker-Volumeobjekt und die gebundene
Continuation.

Der Finalizer erzeugt keine fehlende LQ-400-Continuation-Evidence
nachträglich.

## Keine gefälschte Continuation-Evidence

`volume_absent_evidence_missing` beweist aktuelle Abwesenheit unter offenem
Doppelclaim, aber nicht die vollständige ursprüngliche Prozessbestätigung von
LQ-400.

Der Finalizer darf deshalb keinen Record mit dem LQ-400-Schema, dem Schritt
`remove_exact_volume_once` oder der Behauptung einer empfangenen
Removeantwort erfinden.

Stattdessen dokumentiert getrennte Continuation-Finalization-Evidence den
frisch beobachteten LQ-402-Zustand.

`continuation_evidence_confirmed` bestätigt vorhandene LQ-400-Evidence, ohne
sie umzuschreiben oder zu ersetzen.

## Vorhandenes Volume bleibt nichtterminal

`volume_present` wird ausschließlich zu `investigation_required`.

Dieser Ausgang erzeugt keine Finalization-Evidence und gibt keinen Claim
frei.

LQ-400 hat sein einzelnes Mutationsbudget bereits beansprucht; aktuelle
Volumeanwesenheit erlaubt deshalb weder Blind-Retry noch automatische weitere
Continuation.

Eine spätere Handlung benötigt eine neue ausdrückliche Entscheidung und einen
separaten Vertrag.

LQ-403 erzeugt keine neue Claim- oder Continuation-ID.

## Not found und Conflict

`not_found` bleibt neutral ohne Evidence-, Claim- oder Ressourcenwrite.

Ohne Unterclaim und ohne Continuation-Evidence existiert kein gebundener
Continuation-Abschluss, den dieser Finalizer freigeben dürfte.

`conflict` wird zu `investigation_required` und lässt beide Claims, Evidence
und Ressourcen unverändert.

Fremdbindung wird nicht durch Relabeling, Übernahme, Umbenennung oder
Entfernung repariert.

Technische Nichtverfügbarkeit bleibt ohne Ergebnisobjekt.

## Getrennte Finalization-Evidence

Die eigene private Evidence bindet mindestens:

- Schemaversion und Continuation-Finalization-ID;
- Continuation-Reconciliation-, Continuation- und beide Claim-IDs;
- ursprüngliche Finalization-, Reconciliation-, Lösch- und Dispositions-ID;
- Run, Phase, Source, Image, Compose und exakte Volumeidentität;
- Operation und Scope `data_volume_only`;
- SHA-256 aller gebundenen Autorisierungen und Quellartefakte;
- stabile Retention-, Hold- und Recoveryentscheidungs-IDs;
- frisch beobachteten LQ-402-Zustand;
- kanonischen Finalisierungsausgang;
- sämtliche getrennten Identitätsbindungen;
- UTC-Start- und Abschlusszeit.

Private Details werden nicht in der öffentlichen Ausgabe wiederholt.

## Atomare Evidenceanlage

Finalization-Evidence wird owner-only über exklusive Temporäranlage
vollständig geschrieben und geflusht.

Die finale Datei entsteht atomar; anschließend wird das private
Evidenceverzeichnis synchronisiert.

Der Finalizer liest sie vollständig zurück und prüft semantische sowie
bytegenaue Bindung, bevor Claimfreigabe erreichbar ist.

Teilgeschriebene Temporärdateien oder eine kollidierende finale Datei sind
keine gültige Evidence.

Abweichende vorhandene Evidence wird nie überschrieben.

## Unterclaimfreigabe erst nach Evidence

Nur vollständig zurückgelesene terminale Finalization-Evidence darf die
Freigabe des exakten LQ-400-Continuation-Claims erreichen.

Der Claimpfad wird ausschließlich aus dem SHA-256 der gebundenen
Continuation-Claim-ID abgeleitet.

Ein vorhandener Unterclaim wird vollständig gegen die historische
LQ-400-Bindung validiert, bevor genau diese eine Datei entfernt werden darf.

Ist er bereits abwesend, ist die Freigabe idempotent abgeschlossen.

Suche, Alter, Prefix, Wildcard und Gruppenauswahl existieren nicht.

Der ursprüngliche LQ-394-Claim bleibt offen.

## Unknown Outcome der Claimfreigabe

Ist Unterclaimfreigabe oder Verzeichnissynchronisation technisch mehrdeutig,
bleibt die Finalization-Evidence erhalten und der Ausgang unavailable.

Der exakte Retry liest zuerst dieselbe Evidence und prüft anschließend nur
den exakten LQ-400-Unterclaim.

Vorhandener exakt gebundener Unterclaim erlaubt einen einzelnen erneuten
Freigabeversuch; fehlender Unterclaim bedeutet bereits abgeschlossen.

Der Retry führt LQ-402 nicht erneut aus und erreicht kein Docker.

Fremder oder beschädigter Claim wird niemals entfernt.

## Evidence-Retry

Evidence-Retry verwendet dieselbe Finalization-,
Continuation-Reconciliation-, Continuation- und gesamte historische
Autorisierungskette.

Eine neue ID, neue Autorisierung oder veränderte Evidence ist kein Retry.

Der Retry darf nur den in der Evidence gespeicherten terminalen Ausgang erneut
ausgeben, nachdem die exakte Unterclaimfreigabe abgeschlossen ist.

`not_found` und `investigation_required` erzeugen keine Evidence und besitzen
keinen Evidence-Retry in diesem Slice.

## Weiterer Abschluss

Nach `volume_removal_ready_for_deletion_finalization` oder
`continuation_evidence_confirmed` bleibt der ursprüngliche LQ-394-Claim offen.

Eine spätere frische LQ-398-Ausführung kann die Volumeabwesenheit erneut über
LQ-396 beobachten, eigene ursprüngliche Finalization-Evidence schreiben und
erst danach den LQ-394-Claim freigeben.

LQ-403 startet LQ-398 nicht automatisch und übernimmt dessen Evidence nicht.

## Strikte Writegrenze

Die einzigen erlaubten Writes sind atomare
Continuation-Finalization-Evidence und die spätere Freigabe ausschließlich
des exakten LQ-400-Unterclaims.

Der ursprüngliche Claim, Volume, andere Dockerobjekte, historische Evidence,
Autorisierungen und Clearanceartefakte bleiben unverändert.

Volume-Remove, Mount, Export, SQL, Compose-Down, Prune, Force, Relabeling und
weitere Continuation sind verboten.

Der Finalizer erzeugt keinen neuen Claim und keine Ersatz-ID.

## Geschlossene Ausgänge

Der spätere Finalizer darf ausschließlich liefern:

- `not_found`;
- `continuation_evidence_confirmed`;
- `volume_removal_ready_for_deletion_finalization`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die Ausgabe enthält nur kanonische Schemaversion, feste Operation
`disposable_postgres_volume_deletion_continuation_finalization` und Ausgang.

Run-, Volume-, Claim-, Evidence-, Retention-, Hold-, Recovery-, Identitäts-,
Hash-, Zeit- und Pfaddetails bleiben privat.

## Retention und Nichtwiederverwendung

Continuation-Finalization-, Continuation-Reconciliation-, Continuation-,
Finalization-, Reconciliation-, Lösch- und beide Claim-IDs sowie alle
Autorisierungen, Claims, Evidence und Quellartefakte bleiben mindestens so
lange unterscheidbar, wie Audit, Idempotenz, Retry, Reconciliation oder
übergeordnete Löschfinalisierung davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Claimfreigabe und lokale Volumeabwesenheit beenden die Retention nicht.

Dieser Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Grenzen der Abschlussaussage

Die beiden positiven Finalisierungsausgänge bestätigen nur den
evidence-first Abschluss der exakten lokalen LQ-400-Continuation.

Backups, Exporte, Snapshots, Replikate, Logs und historische Evidence besitzen
eigene Retention- und Dispositionsgrenzen.

Der Finalizer liefert niemals die Aussage „alle Daten entsorgt“.

Vollständige Datenentsorgung bleibt eine übergeordnete
System-of-Record-Aussage.

## Nichtziele und Bundle

LQ-403 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Finalizer, Evidencewriter, Claimrelease,
Inspector, Continuation, LQ-398-Abschluss oder Volume-Remove.

Bundle-Gates bleiben bei 56 Entry Points, 60 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-404 sollte den Evidence-first
Volume-Deletion-Continuation-Finalizer gemäß diesem Vertrag implementieren.

Fake-basierte Tests müssen frischen LQ-402-Inspector, beide terminalen
Finalisierungen, `volume_present`, Conflict, Not-found, ursprünglichen Claim,
atomare Evidence, Unterclaimfreigabe und Evidence-Retry ohne
Ressourcenschreibpfad prüfen.

Die abschließende frische LQ-398-Ausführung und jeder weitere
Volume-Mutationsversuch bleiben separate spätere Slices.
