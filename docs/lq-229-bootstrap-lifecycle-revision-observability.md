# LQ-229 — Bootstrap Lifecycle Revision Observability

## 1. Ergebnis

LQ-229 implementiert den in LQ-228 entschiedenen minimalen Vertrag für die
kontrollierte Übergabe initialer Lifecycle-Revisionen.

`liquent-initial-bootstrap identity` schreibt nun bei frischem Bootstrap und
exakter kanonischer Recovery denselben owner-only Vier-Felder-Shape:

- `user_id`;
- `workspace_id`;
- `user_revision_id`;
- `workspace_revision_id`.

Damit können die regulären User- und Workspace-Lifecycle-Operatoren direkt aus
dem geschützten Bootstrap-Ergebnis gestartet werden.

## 2. Unveränderte Domain-Grenze

Die bestehende `BootstrappedIdentityAuthority` bleibt unverändert und enthält
weiterhin ausschließlich UserId und WorkspaceId.

Der fachliche Bootstrap-Port und der persistente Adapter behalten ihre
Signatur. Es entsteht kein Revisions-Lookup in der Domain und keine neue
Authority-Aussage.

Die zusätzliche Beobachtbarkeit gehört ausschließlich zur kontrollierten
Offline-Prozessgrenze, die den operativen Übergang besitzt.

## 3. Bewahrung der frischen Revisionen

Der Operator übergibt dem bestehenden Bootstrap-Adapter weiterhin getrennte
sichere Generatorfunktionen.

Kleine Wrapper bewahren exakt die beiden Werte, die der Adapter während der
erfolgreichen Transaktion zieht. Es gibt keinen zweiten Generatoraufruf und
keine nachträgliche Ableitung.

Ein erfolgreicher frischer Bootstrap muss pro Domäne genau eine Revision
gezogen haben. Jede unerwartete Abweichung endet detailfrei technisch
nichtverfügbar und erzeugt keinen falschen Resultatshape.

## 4. Atomarer Persistenzbezug

Die bewahrten Werte sind dieselben IDs, die der Adapter atomar speichert als:

- User- beziehungsweise Workspace-Lifecycle-Revision;
- vollständigen initialen Einzelmember;
- jeweiligen Current-Pointer.

UserId, WorkspaceId, Authorities, Revisionen und Pointer bleiben Teil einer
einzigen Datenbanktransaktion.

LQ-229 verändert weder Locking noch Leerheitsprüfung oder Commitverhalten.

## 5. Kanonische Recovery

Die bestehende read-only Recovery liest nun zusätzlich beide Current-
Revisionen aus derselben kanonischen Join-Beziehung.

Ihre vorherigen exakten Count- und Statusbedingungen bleiben bestehen. Damit
existieren jeweils genau eine Revision, ein Member und ein Current-Pointer,
und beide Member binden exakt den aktiven Bootstrap-Nutzer beziehungsweise
Workspace.

Recovery konstruiert die typisierten Revisions-IDs aus den bestätigten
persistierten Werten und erzeugt keine neue ID.

## 6. Gemeinsamer Vier-Felder-Shape

Frischer Erfolg und Recovery laufen vor dem Resultatschreiben in dieselbe
prozesslokale Ergebnisform.

Beide schreiben exakt dieselben vier Feldnamen. Es gibt keinen optionalen,
gemischten oder versionsabhängigen Shape.

Ein verlorenes Ergebnis kann deshalb durch Wiederholung mit einem neuen
leeren Zielpfad bytegleich rekonstruiert werden, solange der Bestand
kanonisch unverändert bleibt.

## 7. Owner-only Dateigrenze

Die bestehende sichere Ergebnislogik bleibt unverändert:

- keine Symlinks;
- owner-only Zielverzeichnis;
- neuer exklusiver temporärer Pfad;
- Dateimodus 0600;
- vollständiger Write und `fsync`;
- atomarer Move;
- kein Überschreiben vorhandener Ziele.

Die Revisionswerte erscheinen weder auf stdout noch stderr.

## 8. Technischer Retry

Wenn der Datenbank-Commit erfolgreich war, aber das Resultatschreiben scheitert,
wird keine Mutation kompensiert und der Bootstrap nicht wieder geöffnet.

Der Operator kann mit einem neuen Resultatpfad erneut aufgerufen werden. Nur
der exakte unveränderte kanonische Bestand liefert `recovered` und dasselbe
Vier-Felder-Ergebnis.

Zusätzlicher, partieller, inaktiver oder regulär mutierter Bestand bleibt
neutral `closed` ohne Detail.

## 9. Übergang zur regulären Nutzeranlage

Der aktualisierte End-to-End-Nachweis liest `user_revision_id` ausschließlich
aus der geschützten Bootstrap-Datei.

Er verwendet den Wert als `expected_revision` für
`liquent-user-lifecycle create`. Die Ziel-UserId bleibt systemgeneriert und
wird erst aus dessen geschütztem Resultat beobachtet.

Es gibt kein injiziertes Revisionswissen und keinen Datenbankquery.

## 10. Übergang zur regulären Workspaceanlage

Der gleiche Nachweis verwendet `workspace_revision_id` als erste erwartete
Workspace-Revision.

Die systemgenerierte zweite UserId wird als expliziter erster
Onboarding-Manager gebunden. Die Ziel-WorkspaceId bleibt ebenfalls intern
erzeugt und verlässt nur das owner-only Operatorresultat.

Damit ist der konkrete LQ-227-Übergabeblocker geschlossen.

## 11. Kein allgemeiner Inspector

LQ-229 ergänzt kein Kommando für Current-, Status-, List-, Dump- oder
Bestandsinspektion.

Nachfolgende reguläre Mutationen geben ihre resultierende Revision bereits
über stabile Change-ID-Retries aus.

Der Bootstrap bleibt ausschließlich für frischen oder exakt kanonisch
rekonstruierbaren Anfangsbestand zuständig.

## 12. Keine Authority-Ausweitung

Die beiden ausgegebenen Revisionen gewähren keine Lifecycle-Authority.

Jede nachfolgende neue Entscheidung löst Actorstatus, dedizierte Authority,
vollständigen aktuellen Bestand und erwartete Revision weiterhin atomar aus
der Persistenz auf.

Entzug wirkt auf spätere neue Entscheidungen. Stale Revisionen werden neutral
abgelehnt.

## 13. PostgreSQL-Nachweis

Der markierte Bootstrap-Operator-Test führt frischen CLI-Bootstrap und exakten
CLI-Retry auf einer disposable PostgreSQL-Datenbank aus.

Er bestätigt den exakten Vier-Felder-Shape, bytegleiches Retry-Ergebnis und
owner-only Modus beider Resultatdateien.

Die bestehenden PostgreSQL-Konkurrenz- und Persistenztests bleiben für
atomaren Bootstrap und reguläre Lifecycle-Creates maßgeblich.

## 14. Aktualisierte Betriebsanleitung

Das Initial-Bootstrap-Runbook nennt nun alle vier Ergebnisfelder.

Es weist `user_revision_id` ausschließlich dem ersten User-Lifecycle-Request
und `workspace_revision_id` ausschließlich dem ersten Workspace-Lifecycle-
Request zu.

Raten, `null`, Shell-History, Tickets, Chat, Logs und direktes SQL bleiben
unzulässige Ersatzwege.

## 15. Keine Migration

Der aktuelle Migration-Head bleibt `20260813_0016`.

LQ-229 ändert keine Tabelle, Spalte, Constraint, Revisionserzeugung oder
persistente Mutation. Alle benötigten Werte waren bereits dauerhaft vorhanden.

Es gibt keine Datenumschreibung für bestehende Installationen.

## 16. Nachweise

SQLite-Tests belegen:

- gleiche Revisions-IDs bei frischem Erfolg und Recovery;
- repr-freie prozesslokale Ergebnisse;
- exakten Vier-Felder-CLI-Shape;
- bytegleichen Retry nach verlorenem Resultat;
- Übergabe beider Revisionen an reguläre Create-Operatoren;
- owner-only Ergebnisse für Bootstrap, Nutzer und Workspace.

Der LQ-227-Audit wurde von einer Fehlstellenbehauptung auf den geschlossenen
Übergang aktualisiert. Runtime und breite Inspect-Grenzen bleiben abwesend.

## 17. Nächster Slice

LQ-230 soll den vollständigen integrierten Shared-Environment-Audit erneut
ausführen.

Er muss den nun erreichbaren leeren Startpfad über zweiten Nutzer, zweiten
Workspace, Authority-Rotation, Membership-/Research-Vergabe und Entzug bis zur
beobachtbaren Runtime-Wirkung führen und Recovery korrekt einordnen.

Er darf keine IDs oder Revisionen injizieren, keinen Produktbestand per SQL
herstellen und keine Production-Freigabe ohne vollständig bestandenen Nachweis
behaupten.
