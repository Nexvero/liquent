# LQ-499 — Authorized Cleanup Revision Mutation and Atomic Clearance Contract

## Ergebnis

LQ-499 definiert die Sicherheitsgrenzen für append-only Cleanupmanagement-,
Hold-, Recovery- und Referenzrevisionen sowie für die atomare Erzeugung einer
positiven Cleanupclearance mit ihrem Attempt.

Der Slice implementiert noch keine Domainwerte, Ports, SQL oder Verdrahtung.

## Vier getrennte Quellen

Management, Hold, Recovery und Referenzen bleiben vier unabhängige Systeme of
Record.

Keine Quelle darf den fehlenden oder negativen Fakt einer anderen Quelle
ersetzen.

Eine gemeinsame generische Allowmutation ist ausgeschlossen.

## Management-Lifecycle-Autorität

Nur eine eigene Cleanupmanagement-Lifecycle-Autorität darf Managementrevisionen
für ein Actor-/Scope-Paar appendieren.

Die zu verwaltende Cleanupfähigkeit autorisiert nicht ihre eigene Vergabe oder
Reaktivierung.

Normale Registryauthority, Workspace-Membership und Researchpermissions reichen
nicht aus.

## Hold-Autorität

Holdrevisionen dürfen ausschließlich aus der autoritativen gemeinsamen Legal-,
Incident-, Audit- und Investigation-Holdentscheidung entstehen.

Ein Cleanupmanager darf weder `clear` noch `blocked` für diese Quelle
behaupten.

Fehlende Teilquellen dürfen nicht lokal als No-Hold interpretiert werden.

## Recovery-Autorität

Recoveryrevisionen benötigen eine eigene autoritative Recovery- und
Reconciliationgrenze.

Terminalität, Prozessabwesenheit oder ein Retentionentscheid erzeugen kein
Recovery-Clear.

Ein offener oder unbekannter Recoverybedarf bleibt fail-closed.

## Referenz-Autorität

Referenzrevisionen entstehen nur aus einer autoritativen vollständigen Prüfung
aller betroffenen persistenten und operativen Referenzen.

Eine einzelne Tabellenabwesenheit oder ein caller-gelieferter Leerzustand ist
kein Clear-Nachweis.

Der Cleanupmanager kann diese Entscheidung nicht selbst ausstellen.

## Authentifizierter Actor

Ein `SessionPrincipal` kann die Identität eines aufrufenden Actors liefern.

Er trägt keine Authority für irgendeine der vier Mutationsgrenzen.

Actorstatus und benötigte Lifecycleauthority werden aktuell aus den jeweiligen
Systemen of Record gelesen.

## Interne Zielbindung

User, Scope und Directory werden anhand stabiler interner IDs serverseitig
aufgelöst.

Caller dürfen weder Status, Rolle, Authority, Scopeaktivität, Directoryhandle
noch Retired-Fakten als vertrauenswürdige Behauptung mitgeben.

Ein Request enthält höchstens die gewünschte geschlossene Zustandsänderung und
eine Idempotenzidentität.

## Geschlossene gewünschte Zustände

Managementmutation kann ausschließlich `active` oder `inactive` verlangen.

Die drei Zielquellen können ausschließlich `clear` oder `blocked` verlangen.

Freie Rollen, Permissionstrings, Reason-to-Allow oder Boolean-Allowfelder sind
unzulässig.

## Interne Revisionsidentitäten

Neue Revisions-IDs werden durch die kontrollierte Grenze erzeugt oder aus einer
vorher serverseitig reservierten nichtwiederverwendbaren Identität übernommen.

Sie werden nicht aus Actor, Scope, Directory, Status oder Zeit abgeleitet.

Eine Identität bleibt dauerhaft an genau einen Intent gebunden.

## Append-only Sequenzierung

Die nächste Sequenz wird innerhalb derselben Datenbanktransaktion unter
geeigneter Serialisierung aus dem aktuellen vollständigen Bestand bestimmt.

Caller liefern keine autoritative Sequenznummer.

UPDATE, DELETE, Reorder und Überschreiben historischer Revisionen sind
ausgeschlossen.

## First-write-Regel

Die erste Revision ist nur zulässig, wenn die Quelle für das exakte Ziel noch
keine Revision besitzt und die zuständige Authority dies autorisiert.

Abwesenheit erteilt nicht automatisch Active oder Clear.

Bootstrap oder Migration erzeugen keine erste positive Revision.

## Erwartete Vorgängerrevision

Nachfolgende Mutationen müssen die erwartete aktuelle Revisions-ID als
Concurrency-Bindung tragen.

Die ID ist keine Authoritybehauptung; der Server vergleicht sie mit der aktuell
höchsten Revision.

Abweichung liefert eine detailarme fachliche Kollision und schreibt nichts.

## Revocation und Blockierung

Inactive und Blocked sind normale append-only Zustandsrevisionen.

Sie müssen nach erfolgreichem Commit jede spätere Clearanceentscheidung
sperren.

Frühere positive Revisionen bleiben Historie und dürfen nicht wieder als
aktuell ausgewählt werden.

## Idempotenter Retry

Ein Retry mit derselben Mutationsidentität und exakt demselben Ziel, Vorgänger
und gewünschten Zustand liefert die bereits persistierte Revision.

Dieselbe Identität mit abweichendem Intent ist Konflikt.

Ein Retry erzeugt keine zweite Sequenz und keine neue Zeit.

## Serverseitige Zeit

`resolved_at` und `decided_at` entstehen innerhalb der kontrollierten
Transaktion aus einer serverseitigen aware-UTC-Uhr.

Callerzeiten werden weder persistiert noch für Reihenfolge oder Authority
verwendet.

Zeit darf nicht vor den relevanten dauerhaften Ziel- und Vorgängerfakten liegen.

## Clearance ist keine fünfte Authorityquelle

Die aggregierte Clearance erzeugt keine Management-, Hold-, Recovery-,
Referenz- oder Retentionauthority.

Sie bindet ausschließlich bereits vorhandene aktuelle positive Revisionen an
einen konkreten Cleanupattempt.

Ein Operator darf keine fertige Evidencezusammenstellung einreichen.

## Interner Clearance-Koordinator

Nur eine interne kontrollierte Composition darf eine positive Clearance
erzeugen.

Ihr Eingang ist der geschlossene Cleanuprequest aus Attempt-ID, Actor-ID und
Directory-ID.

Alle weiteren Fakten werden innerhalb der Composition serverseitig aufgelöst.

## Atomare Attempt- und Clearanceerzeugung

Für einen neuen produktionsfähigen Cleanup müssen Attemptzeile und
Clearancezeile in derselben serialisierten Datenbanktransaktion entstehen.

Entweder beide Bindungen committen oder keine von beiden.

Ein vorzeitig sichtbarer Started-Attempt ohne Clearance darf keine physische
Wirkung öffnen.

## Keine Adoption alter Attempts

Ein bereits separat persistierter Attempt ohne Clearance wird nicht
nachträglich als atomar freigegeben.

Für einen neuen sicheren Versuch ist eine neue nichtwiederverwendbare
Attempt-ID erforderlich.

Historische LQ-494-Records bleiben lesbar, aber nicht productionwirksam.

## Transaktionale Revalidierung

Vor dem Insert liest der Koordinator innerhalb derselben Entscheidung erneut:

- aktiven persistenten Actor;
- aktiven Handoffscope aus dem terminalen Journal;
- aktuellen vollständigen Retired-Wert;
- aktuelle Eligible-Retentionentscheidung;
- aktuelle Active-Managementrevision;
- aktuelle Clear-Holdrevision;
- aktuelle Clear-Recoveryrevision;
- aktuelle Clear-Referenzrevision;
- genau einen vollständigen terminalen Journalview.

Kein vorab gelesener LQ-498-Snapshot ersetzt diese Revalidierung.

## Gebundene Evidenz

Die Clearance persistiert ausschließlich die bereits in Revision 0036
vorgesehenen IDs und die serverseitige Clearancezeit.

Decision, Management, Hold, Recovery, Referenzen und Terminal-Observation
müssen zum selben Actor-, Scope-, Directory-, Handle- und Journalziel gehören.

Caller-gelieferte Evidence-Dicts oder Allowflags werden nicht akzeptiert.

## Clearance-Retry

Ein Retry derselben Attempt-ID darf nur dann denselben positiven Wert liefern,
wenn Request, Clearance-ID und sämtliche gebundenen Revisionen exakt
übereinstimmen und weiterhin aktuell positiv sind.

Eine abweichende Bindung ist Konflikt.

Eine inzwischen widerrufene Bindung wird nicht als erfolgreicher Retry
zurückgegeben.

## Konkurrenz

Gleichzeitige Revisionmutationen und Clearanceerzeugung werden so serialisiert,
dass keine Clearance hinter einer bereits committeten höheren negativen
Revision entstehen kann.

Unique-Constraints bleiben letzte Integritätssperre, ersetzen aber nicht den
fachlichen Current-State-Vergleich.

Technische Deadlocks dürfen nicht als fachliche Freigabe behandelt werden.

## Neutrale Abwesenheit und Zurückweisung

Ein unbekanntes Ziel oder eine fehlende benötigte Authority kann an einer
nichtoffenlegenden Grenze neutral abwesend bleiben.

Bekannte Vorgängerabweichung, ID-Kollision, negative aktuelle Revision oder
inkompatibler Retry werden detailarm zurückgewiesen.

Der Vertrag benennt keinen neuen Exceptiontyp.

## Technische Unverfügbarkeit

Mehrdeutige Systeme-of-Record-Fakten, beschädigte Revisionen, unmögliche
Sequenzen, Journaldivergenz und Transaktionsfehler bleiben detailfreie
technische Unverfügbarkeit.

Interne SQL-, Identifier-, Authority- oder Zielinformationen verlassen die
Grenze nicht.

## Dauerhafte Historie

Revisionen, Clearance-IDs und Attempt-IDs werden nicht gelöscht oder neu
zugewiesen.

Retention muss mindestens alle für Audit, Revocation und Retryprüfung nötigen
Bindungen erhalten.

Physischer Byte-Cleanup verkürzt diese Untergrenze nicht.

## Keine Dateioperation

Revisionmutation und Clearanceerzeugung öffnen, inspizieren, verändern oder
entfernen keine Datei und kein Verzeichnis.

Positive Clearance ist nur persistente Vorbedingung für einen späteren
physischen Slice.

Unlink, Rmdir und rekursiver Cleanup bleiben geschlossen.

## Keine Entscheidung in diesem Slice

LQ-499 ergänzt keine Domainklasse, Portsignatur, Tabelle, Migration, SQL,
Adapterimplementation, Testschnittstelle, CLI oder Verdrahtung.

Head und Migrationsanzahl bleiben `20260825_0036` und 36.

Es gibt keinen Grant-, Revoke-, Block-, Clear- oder Clearance-Schreibpfad.

## Nächster Slice

LQ-500 sollte die geschlossenen Commands, Resultate, Konflikte und Ports für die
vier getrennten Revisionmutationen und die atomare Attempt-/Clearancecomposition
implementieren.

Persistenzimplementation, Production-Wiring und physischer Cleanup folgen
weiterhin getrennt.
