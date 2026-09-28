# LQ-334 — Disposable PostgreSQL Recovery Disposition Contract

## Zweck

LQ-334 definiert die Entscheidung nach vollständig finalisierter LQ-332/333-
Reconciliation-Evidence für einen unbekannten LQ-330-Ausgang.

Der Vertrag trennt strikt:

- unverändertes Retain;
- Zulässigkeit eines vollständig neuen autorisierten Runs;
- mögliche spätere Cleanup-Prüfung für exakt gebundene isolierte Ressourcen.

Dieser Slice implementiert keinen Resolver, Operator oder Dockeraufruf und
entfernt keine Ressource.

## Maßgebliche Evidence

Eine Dispositionsentscheidung darf ausschließlich aus dem privaten System of
Record abgeleitet werden.

Mindestens vollständig zu prüfen sind:

- historische LQ-330-Staging-Autorisierung;
- LQ-331-Reconciliation-Autorisierung;
- finale LQ-332-Reconciliation-Evidence;
- gegebenenfalls LQ-333-Claim-Reconciliation-Autorisierung und -Evidence;
- Abwesenheit ungelöster Claims derselben Reconciliationkette;
- SHA-256 der exakten Evidencebytes;
- Run, Phase, Source, Application-Image und Composebindung;
- getrennte Identitäten und UTC-Zeitwerte.

Ein caller-gelieferter Ausgang, Ressourcenstatus, Allow-Boolean, Rollenname
oder frei formulierter Cleanupgrund ist keine Evidence.

## Aktuelle Zustandsquelle

Der fachlich maßgebliche Ressourcenstatus stammt aus der finalen LQ-332-
Evidence:

- `absent`;
- `isolated`;
- `conflict`.

LQ-333-Handoffs wie `evidence_confirmed`, `absence_finalized`,
`isolation_finalized` oder `conflict_finalized` bestätigen die
Finalisierungsfolge, ersetzen aber nicht den zugrunde liegenden Zustand.

`already_finalized` ist ebenfalls nur ein Handoff. `not_found` beweist weder
Abwesenheit noch Isolation.

Fehlende, beschädigte, anders gebundene oder widersprüchliche Evidence ist
technisch unavailable und darf nicht als `conflict` oder `absent` erraten
werden.

## Geschlossene Dispositionen

Der spätere read-only Resolver darf ausschließlich einen dieser neutralen
Ausgänge liefern:

- `retain`;
- `new_run_eligible`;
- `cleanup_review_eligible`;
- `investigation_required`;
- technisch unavailable ohne Ergebnis.

Kein Ausgang ist selbst ein Docker-, Cleanup-, Runstart-, Staging-,
Deployment- oder Productionauftrag.

Der Resolver akzeptiert keine gewünschte Disposition vom Caller.

## Retain als sichere Untergrenze

`retain` bedeutet ausschließlich, dass keine Ressource und keine Evidence
verändert werden darf.

Retain ist die sichere Untergrenze für jeden vollständig lesbaren Zustand,
wenn die strengeren Voraussetzungen einer anderen Disposition nicht erfüllt
sind.

Es verlängert keine Autorisierung, ändert keinen früheren Phasenstatus und
erklärt Ressourcen nicht nachträglich zu Produktbestand.

Retention darf nicht durch Alter, Kosten, Namenskollision oder fehlende
Operatoraktivität automatisch in Cleanup umgedeutet werden.

## Neuer Run nur nach bestätigter Abwesenheit

`new_run_eligible` ist ausschließlich zulässig, wenn gemeinsam gilt:

- finale LQ-332-Evidence lautet exakt `absent`;
- eine gegebenenfalls notwendige LQ-333-Finalisierung ist vollständig;
- kein ursprünglicher oder Claim-Reconciliation-Claim bleibt offen;
- Evidencekette und Hashes stimmen vollständig überein;
- keine gleichnamige Runressource ist aus widersprüchlicher Evidence bekannt;
- der frühere Run wird nie wiederverwendet oder fortgesetzt.

Der neue Run benötigt später eine vollständig neue Staging-Autorisierung mit
neuer nicht wiederverwendeter Run-ID, neuen Identitäten, neuem Zeitfenster und
neu abgeleiteten Ressourcennamen.

Source, Images und Compose dürfen nur aufgrund der neuen Autorisierung gleich
sein; sie werden nicht aus der alten Autorisierung geerbt.

`new_run_eligible` startet LQ-330 nicht. Ein späterer Operator muss die neue
Runautorisierung unabhängig validieren.

## Isolierter Bestand bleibt zunächst erhalten

Finales `isolated` beweist einen exakt rungebundenen gesunden
PostgreSQL-Bestand zum Reconciliationzeitpunkt.

Dieser Bestand darf nicht als abwesend behandelt und nicht durch einen neuen
Run mit derselben ID übernommen werden.

Ohne zusätzliche aktuelle Dispositionsevidence lautet der Ausgang `retain`.

`cleanup_review_eligible` ist nur eine read-only Aussage, dass eine separate
Cleanup-Autorisierung überhaupt geprüft werden darf. Sie ist nur möglich,
wenn zusätzlich nachgewiesen ist:

- vollständige ursprüngliche Isolationsevidence;
- keine ungelösten Claims;
- kein später gestartetes Migration-Gate;
- kein Control-Plane- oder Research-Worker-Start für diesen Run;
- keine spätere Phase-Evidence mit möglichem Produkt- oder Datenbankeffekt;
- keine andere Run-, Staging- oder Productionbindung der Ressourcen;
- unveränderte Ableitung aller vier Ressourcennamen.

Fehlt einer dieser Nachweise, bleibt der Bestand `retain`.

## Conflict ist niemals Cleanupgrundlage

Finales `conflict` bedeutet, dass der sichtbare Bestand nicht vollständig und
ausschließlich dem disposable Run zugeordnet werden konnte.

Die einzige neutrale Disposition ist `investigation_required`.

Conflict gewährt weder Cleanupprüfung noch neuen Run. Er darf nicht durch
erneutes Labeln, Umbenennen, teilweise Entfernen oder Auswahl vermeintlich
passender Einzelobjekte bereinigt werden.

Ähnliche Namen, teilweise Ressourcen, fremde Labels, externe Netze, andere
Volumes oder unklare Imagebindung bleiben außerhalb jedes Mutationsbudgets.

## Not found und offene Claims

LQ-333-`not_found` ist kein Abwesenheitsnachweis. Ohne finale gebundene LQ-332-
Evidence lautet die Disposition technisch unavailable, nicht
`new_run_eligible`.

Ein offener ursprünglicher oder Claim-Reconciliation-Claim bedeutet ebenfalls
unavailable. Der Dispositionsresolver führt keine weitere Reconciliation aus
und entfernt keinen Claim.

Ein späterer kontrollierter Claim-Reconciliation-Versuch bleibt eine separate
Operation mit neuer Autorisierung.

## Separate künftige Cleanup-Autorisierung

Selbst `cleanup_review_eligible` gewährt kein Löschrecht.

Ein späterer Cleanupvertrag muss eine neue owner-only, eng zeitgebundene
Autorisierung verlangen, die mindestens bindet:

- stabile nicht wiederverwendbare Cleanup-ID;
- ursprüngliche Run- und Reconciliationkette;
- SHA-256 aller maßgeblichen Evidenceobjekte;
- Phase `disposable_postgres`;
- Source-, Image- und Composebindung;
- getrennte Cleanup-Executor-/Autorisiereridentitäten;
- Operation exakt `remove_disposable_postgres_resources`;
- ausdrückliche Einbeziehung oder Ausschließung des Datenvolumes.

Eine allgemeine Adminrolle, Membership, Researchpermission oder
caller-geliefertes Delete-Boolean reicht nicht aus.

## Volumenlöschung ist gesondert destruktiv

Container- oder Netzwerkentfernung impliziert niemals die Erlaubnis, das
PostgreSQL-Datenvolume zu löschen.

Volumenlöschung benötigt eine ausdrückliche unveränderliche Autorisierungs-
Bindung und den erneuten Nachweis, dass keine Migration, kein Seed, Restore,
Produktbestand oder späterer Stagingeffekt erreicht wurde.

Kann dies nicht rein aus autoritativer Evidence bewiesen werden, bleibt das
Volume erhalten, selbst wenn Container und Netze später getrennt als sicher
entfernbar beurteilt würden.

Dieser Vertrag trifft keine konkrete Backup-, Export- oder Retentionfrist.

## Anforderungen an einen späteren Cleanup-Operator

Vor dem ersten Effekt muss ein späterer Operator alle Ressourcen erneut
read-only prüfen und exakt gegen Evidence und Cleanup-Autorisierung binden.

Er darf kein allgemeines `compose down`, Projekt-Prune, System-Prune,
Wildcard-, Labelgruppen- oder Prefixcleanup verwenden.

Jede Ressource muss einzeln exakt adressiert werden. Nach dem ersten Effekt
führt ein unklarer Ausgang zu Unknown Outcome ohne Retry oder Fortsetzung.

Entfernung benötigt Evidence-first-Konkurrenzordnung und eigene spätere
Reconciliation. Ein teilweise erfolgtes Cleanup darf nicht als vollständiger
Erfolg ausgegeben werden.

LQ-334 entscheidet noch keine konkrete Reihenfolge, Docker-argv, Timeout- oder
Stopppolicy.

## Neutraler read-only Output

Ein späterer Resolver darf nur kanonische Schema-Version, Operation und eine
der geschlossenen Dispositionen ausgeben.

Run-, Evidence-, Claim-, Ressourcen-, Digest-, Identitäts-, Zeit- und
Pfaddetails bleiben privat.

Technische Nichtverfügbarkeit bleibt detailfrei ohne Ergebnisobjekt.

## Retention und Nichtwiederverwendung

Run-ID, Reconciliation-IDs, Cleanup-ID, Autorisierungen, Claims und Evidence
müssen mindestens so lange unterscheidbar bleiben, wie Audit, Retry,
Disposition oder Interpretation unbekannter Ausgänge darauf angewiesen sind.

Keine ID oder Evidence darf unter neuer Bindung oder Bedeutung wiederverwendet
werden. Ein neuer Run erhält immer eine neue Run-ID.

Dieser Vertrag legt keine konkrete Frist, Tabelle, Schema- oder
Archivierungsstrategie fest.

## Nichtziele

LQ-334 implementiert keinen Resolver, Command, Claim, Evidencewriter,
Dockerprozess, neuen Run oder Cleanup.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Produkt- oder Production-Wiring-Änderung.

Bundle-Gates bleiben bei 32 Entry Points, 36 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-335 sollte zuerst den strikt read-only Dispositionsresolver implementieren.
Er muss die vollständige LQ-332/333-Evidencekette aus dem privaten System of
Record laden und ausschließlich die geschlossenen neutralen Ausgänge liefern.
Cleanup bleibt auch dort ausdrücklich unimplementiert.
