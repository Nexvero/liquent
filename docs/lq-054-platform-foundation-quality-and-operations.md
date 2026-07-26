# LQ-054 — Platform Foundation Quality and Operations

## Status

- Qualitätsziele und Betriebsmodell für Slice 0 definiert.
- Ausgangslage: ein eigener VPS mit 6 vCPU, 12 GB RAM und 100 GB NVMe.
- Bestehendes, verifiziertes Host-Bootstrap als Infrastruktur-Baseline anerkannt.
- Keine Programmiersprache, kein Framework und keine Datenbank ausgewählt.
- Keine Produktionslogik, Runtime-Abhängigkeit oder VPS-Konfiguration geändert.

## 1. Zweck und Geltungsbereich

LQ-054 übersetzt die Produkt- und Plattformgrenzen aus LQ-053 in messbare
Qualitäts- und Betriebsanforderungen. Diese Anforderungen sind der Maßstab für
die spätere Technologieauswahl und Slice-0-Implementierung.

Slice 0 stellt noch keine Trading-Funktion bereit. Sein Ergebnis ist eine
verlässliche Plattformbasis, auf der Slice 1 sicher entwickelt und betrieben
werden kann:

- reproduzierbarer Build,
- kontrolliertes Deployment,
- sichere Konfiguration und Secrets-Grenzen,
- Health, Readiness, Logs, Metriken und Alarmierung,
- Backup, Restore und dokumentierte Recovery,
- belastbare Ressourcen- und Betriebsgrenzen.

## 2. Ausgangslage und Annahmen

### 2.1 Verifizierter Hostzustand

Der aktuelle VPS besitzt:

- Ubuntu 26.04 LTS,
- schlüsselbasierten administrativen SSH-Zugang,
- deaktivierten Root- und Passwort-Login,
- aktive Host-Firewall mit öffentlichen Ports 22, 80 und 443,
- containerisierte Laufzeit mit gehärteter Konfiguration,
- getrennte Netze für Public, Application, Data und Observability,
- automatische Sicherheitsupdates ohne unkontrollierten Auto-Reboot,
- idempotentes, manifestbasiertes Host-Bootstrap mit Rollback.

Diese Baseline wird nicht in die Anwendung kopiert. Sie bleibt eine eigene
Infrastrukturverantwortung.

### 2.2 Betriebsannahmen Slice 0/1

- Ein VPS ist der einzige Produktionshost.
- Es gibt noch keinen Live- oder produktiven Paper-Betrieb.
- Entwicklung und Tests laufen lokal oder in CI, nicht im Produktionskontext.
- Production und dauerhafte Staging-Workloads teilen nicht unkontrolliert
  denselben Zustand.
- Ein einzelner benannter Operator darf deployen; jede Aktion bleibt
  nachvollziehbar.
- Ausfall des VPS ist möglich und wird durch Recovery, nicht durch behauptete
  Hochverfügbarkeit adressiert.

## 3. Serviceklassen

| Klasse | Beispiele | Kritikalität Slice 0/1 | Betriebsregel |
|---|---|---:|---|
| Edge & Control | TLS, Routing, Health, spätere Nutzeraktionen | hoch | Vorrang vor Research-Last |
| Product Application | Workspace- und Evidence-Workflow | mittel | kontrolliert degradierbar |
| Research Jobs | Backtests und Reports | niedrig | abbrechbar, begrenzt, wiederholbar |
| Data & State | persistenter Produktzustand und Artefakte | hoch | kein öffentlicher Zugriff; Backuppflicht |
| Observability | Logs, Metriken, Alarmzustände | mittel | Ausfall darf Primärdienst nicht mitreißen |

Live Automation erhält später eine eigene höchste Serviceklasse und ist nicht
Bestandteil dieser Entscheidung.

## 4. Service Level Objectives

Die Ziele sind interne Engineering-SLOs, keine vertraglichen SLAs.

| Qualitätsmerkmal | Slice-0/1-Ziel | Messung |
|---|---:|---|
| Monatliche Verfügbarkeit | 99,5 %, geplante Wartung separat ausgewiesen | erfolgreicher externer Health-Check |
| Health-Erkennung | Ausfall innerhalb von 2 Minuten erkannt | Checkintervall und Alarmzeitpunkt |
| Operator-Alarm | kritischer Ausfall innerhalb von 5 Minuten zugestellt | Alarmereignis bis bestätigter Kanal |
| Interaktive Antwortzeit | 95 % der normalen Control-Aktionen unter 500 ms serverseitig | Request-Metrik ohne Netzwerkzeit des Nutzers |
| Read-Heavy Ansichten | 95 % unter 1 Sekunde serverseitig | Request-Metrik |
| Research-Annahme | Jobannahme unter 2 Sekunden | Auftrag bis persistierter Jobstatus |
| Deployment | reguläre Promotion unter 15 Minuten | Start bis bestandener Smoke Check |
| Rollback | letzte bekannte Version unter 15 Minuten wieder aktiv | Freigabe bis Readiness |
| Auditierbarkeit | 100 % kritischer Zustandsaktionen mit Actor, Zeit und Correlation ID | Audit-Check |

Die Verfügbarkeit von 99,5 % entspricht maximal rund 3 Stunden 39 Minuten
ungeplanter Ausfallzeit in einem 30-Tage-Monat. Bei ausgeschöpftem Error Budget
haben Stabilität und Ursachenbehebung Vorrang vor neuen Funktionen.

## 5. Health- und Readiness-Modell

Health beantwortet, ob ein Prozess lebt. Readiness beantwortet, ob er sicher
Nutzerverkehr übernehmen darf. Beide Zustände dürfen nicht vermischt werden.

### 5.1 Liveness

- lokal und ohne abhängige Netzwerkdienste auswertbar,
- erkennt blockierte oder abgestürzte Prozesse,
- löst keinen fachlichen Schreibvorgang aus,
- darf nicht durch eine langsame optionale Abhängigkeit fehlschlagen.

### 5.2 Readiness

- prüft nur zwingende Abhängigkeiten des jeweiligen Prozessprofils,
- wird bei laufender Migration, inkonsistentem Zustand oder fehlender
  Kernpersistenz negativ,
- verhindert neue Nutzerarbeit, ohne Diagnosezugriff zu blockieren,
- liefert einen maschinenlesbaren Status und einen operatorgeeigneten Grund.

### 5.3 Dependency Health

Abhängigkeiten erhalten getrennte Zustände für erreichbar, degradiert,
veraltet und nicht verfügbar. Research-Stau darf beispielsweise die Control
Plane nicht als tot markieren.

## 6. Deployment- und Releaseanforderungen

```text
Feature Branch → Checks → Review → Main → unveränderliches Artefakt
  → manuelle Production-Freigabe → Migration Gate → Deployment
  → Readiness → Smoke Check → abgeschlossen oder Rollback
```

Pflichtregeln:

1. Kein Deployment aus einem lokalen, uncommitteten Arbeitsverzeichnis.
2. Jedes Artefakt verweist auf Commit und Build-Identität.
3. Production-Promotion erfordert eine explizite menschliche Freigabe.
4. Secrets sind kein Bestandteil des Artefakts oder Repositorys.
5. Konfigurationsvalidierung erfolgt vor Prozessstart.
6. Datenänderungen besitzen ein eigenes Gate und eine Recovery-Strategie.
7. Readiness und Smoke Check entscheiden über Abschluss oder Rollback.
8. Direkte Produktionsänderungen per Editor oder ad-hoc Kopie sind verboten.
9. Deploymentereignisse werden mit Actor, Artefakt und Ergebnis protokolliert.
10. Der Edge-Proxy bleibt der einzige öffentlich erreichbare Anwendungsweg.

## 7. Umgebungsmodell

| Umgebung | Zweck | Persistenter Produktionszustand | Externe Trading-Verbindung |
|---|---|---:|---:|
| Local | Entwicklung und schnelle Tests | nein | nein |
| CI | reproduzierbare automatisierte Checks | nein | nein |
| Preview | optionales Review eines Changes | nein | nein |
| Production | Slice-1-Nutzerbetrieb | ja | nein |

Ein dauerhaftes Staging auf demselben VPS wird für Slice 0 nicht vorausgesetzt.
Vor produktivem Paper-Betrieb ist jedoch eine separat isolierte Staging-Umgebung
verbindlich. Sie darf nicht dieselben Secrets oder persistenten Daten wie
Production verwenden.

## 8. Backup, Restore und Recovery

### 8.1 Schutzklassen

| Schutzklasse | Beispiele | Ziel-RPO | Ziel-RTO |
|---|---|---:|---:|
| A — Konfiguration/Build | Git, deklarative Konfiguration, Build-Metadaten | 0 durch versionierte Quelle | 2 Stunden |
| B — Produktzustand | Nutzer-, Workspace-, Strategy- und Experimentmetadaten | 24 Stunden in Slice 1 | 4 Stunden |
| C — Artefakte | importierte Snapshots, Resultate, Reports | 24 Stunden | 8 Stunden |
| D — regenerierbar | Cache, temporäre Jobs, abgeleitete Vorschauen | kein Backup erforderlich | Wiederaufbau unter 2 Stunden |

Vor produktivem Paper-Betrieb werden RPO/RTO separat verschärft.

### 8.2 Backupregeln

- Backups liegen verschlüsselt außerhalb des VPS.
- Tägliche Sicherung mit mindestens 7 täglichen und 4 wöchentlichen Ständen.
- Monatliche Sicherungen werden mindestens 6 Monate aufbewahrt.
- Backupjobs besitzen Erfolg, Dauer, Umfang und Alter als Metriken.
- Ein fehlendes oder zu altes Backup erzeugt einen kritischen Alarm.
- Secrets werden nur über ein gesondertes, zugriffsbeschränktes Verfahren
  gesichert; niemals über Git.

### 8.3 Restore-Nachweis

- Vor Slice-1-Produktionsfreigabe findet ein vollständiger Restore-Test statt.
- Danach mindestens quartalsweise und nach wesentlichen Persistenzänderungen.
- Ein Restore gilt erst als bestanden, wenn Anwendung, Referenzen,
  Berechtigungen und Stichproben fachlich geprüft wurden.
- Ergebnis, Dauer, Abweichungen und Owner werden dokumentiert.

## 9. Observability und Audit

### 9.1 Technische Signale

- strukturierte Logs mit Timestamp, Severity, Service Role und Correlation ID,
- Requestanzahl, Fehlerrate und Antwortzeit,
- Jobannahme, Laufzeit, Abbruch, Fehler und Queue-Alter,
- CPU, RAM, Disk, Inodes und Netzwerkzustand,
- Health/Readiness und Neustartzähler,
- Backupalter, Backupfehler und Restore-Teststatus.

### 9.2 Audit Trail

Audit ist nicht gleich Log. Kritische Produktaktionen benötigen mindestens:

- Actor und Organisationskontext,
- Aktion und betroffenes Objekt,
- vorherigen und neuen Zustand oder belastbare Referenz,
- Zeitpunkt und Correlation ID,
- Quelle der Aktion,
- Ergebnis und Fehlergrund.

Auditdaten dürfen nicht still überschrieben werden und enthalten keine Secrets.

### 9.3 Alarmklassen

| Klasse | Beispiel | Reaktion |
|---|---|---|
| Critical | öffentlich nicht erreichbar, persistenter Zustand unlesbar, Backup überfällig | sofortige Benachrichtigung; neue Deployments stoppen |
| Warning | Disk über 70 %, erhöhte Fehlerquote, Research-Stau | innerhalb eines Arbeitstags prüfen |
| Info | Deployment abgeschlossen, Backup erfolgreich | Ereignis protokollieren |

## 10. Sicherheitsanforderungen

- MFA für GitHub- und OVH-Administrationskonten.
- Keine gemeinsam genutzten persönlichen Zugangsdaten.
- Least Privilege für Host, Repository und Deployment.
- Secretwerte weder in Git, Logs, Build-Artefakten noch Fehlermeldungen.
- Kritische Sicherheitsupdates innerhalb von 24 Stunden bewerten und
  einspielen; sonstige sicherheitsrelevante Updates innerhalb von 7 Tagen.
- Kontrolliertes Wartungsfenster für erforderliche Neustarts.
- Abhängigkeiten und Artefakte müssen nachvollziehbare Herkunft besitzen.
- Administrative Zugriffe und Production-Promotions werden protokolliert.
- Externe Daten-, Broker- oder AI-Zugriffe sind in Slice 0 nicht erlaubt.
- Ein Sicherheitsvorfall stoppt Releases bis Eindämmung und Zustandsklärung.

## 11. Kapazitäts- und Ressourcengrenzen

Der einzelne VPS ist eine bewusste Kosten- und Komplexitätsgrenze, kein
unbegrenzter Compute-Pool.

### 11.1 Reserven

- Im Normalbetrieb bleiben mindestens 30 % RAM für Spitzen und Recovery frei.
- Dauerhafte CPU-Auslastung über 70 % wird untersucht.
- Disk-Warnung bei 70 %, kritisch bei 85 %.
- Kritische Control-/Data-Prozesse besitzen Vorrang vor Research Jobs.
- Ein Research Job darf ohne neue Kapazitätsfreigabe höchstens 50 % der CPU und
  40 % des RAM beanspruchen.
- Bis zur Lastmessung läuft höchstens ein schwerer Research Job gleichzeitig.

### 11.2 Skalierungssignale

Eine Architektur- oder Hoständerung wird geprüft, wenn mindestens eines gilt:

- Error Budget wird durch Ressourcenengpässe wiederholt ausgeschöpft,
- 95-%-Latenzziele werden in drei aufeinanderfolgenden Messfenstern verfehlt,
- Queue-Alter überschreitet wiederholt das definierte Jobziel,
- freie RAM-Reserve fällt im Normalbetrieb unter 30 %,
- Diskwachstum gefährdet innerhalb von 30 Tagen die 70-%-Schwelle,
- Recovery- oder Backupziele sind auf dem Einzelhost nicht mehr erreichbar.

Die erste Reaktion ist Kapazitätsmessung und Prozessisolation, nicht automatisch
eine Microservice-Aufteilung.

## 12. Betriebsrollen und Runbooks

Für Slice 0 genügt ein kleiner Rollenrahmen; Verantwortungen bleiben trotzdem
explizit:

| Rolle | Verantwortung |
|---|---|
| Product Owner | Scope, Produktgrenze und Releasefreigabe |
| Code Reviewer | Qualitäts- und Sicherheitsprüfung der Änderung |
| Operator | Deployment, Monitoring, Backup und Recovery |
| Incident Owner | Koordination, Timeline und Abschluss eines Vorfalls |

Vor Production Slice 1 müssen Runbooks vorhanden sein für:

- Dienst nicht erreichbar,
- fehlgeschlagenes Deployment,
- Rollback,
- Disk-/Ressourcenengpass,
- Backupfehler,
- Restore,
- kompromittiertes Secret,
- verlorener administrativer Zugriff.

## 13. Go-Live-Gates für Slice 0

Slice 0 ist abgeschlossen, wenn:

- Build und Deployment aus einem unveränderlichen Artefakt reproduzierbar sind,
- Production-Secrets außerhalb des Repositorys liegen,
- Health und Readiness extern und intern geprüft werden,
- Logs, Kernmetriken und mindestens ein kritischer Alarm funktionieren,
- Ressourcenlimits und Disk-Alarme aktiv sind,
- Offsite-Backup erfolgreich läuft,
- ein Restore praktisch bestanden wurde,
- Rollback innerhalb des Zielwerts getestet ist,
- Deployment und kritische Aktionen nachvollziehbar sind,
- kein Daten-, Broker-, AI- oder Tradingzugriff aktiviert ist,
- der Betrieb mit den vorhandenen 6 vCPU, 12 GB RAM und 100 GB NVMe innerhalb
  der definierten Reserve bleibt.

## 14. Einfluss auf die Technologieauswahl

Eine spätere Option ist nur geeignet, wenn sie nachweisbar unterstützt:

- modularen Monolithen und klare interne Grenzen,
- reproduzierbare Builds und unveränderliche Artefakte,
- getrennte Prozessrollen auf einem VPS,
- sichere Migration, Backup und Restore,
- Health, Readiness, strukturierte Logs, Metriken und Tracing-Kontext,
- Ressourcenlimits und kontrollierte Research Jobs,
- lokale Entwicklung, CI und manuelle Production-Promotion,
- evolutionäre Extraktion ohne Neuentwurf des Produktmodells.

Ein außerhalb des Repositorys vorhandener früher Technologievorschlag gilt bis
zur separaten LQ-055-Entscheidung als Diskussionsgrundlage, nicht als bindender
Standard.

## 15. Nächste Entscheidung

LQ-055 bewertet konkrete Architektur- und Technologieoptionen gegen die in
diesem Dokument festgelegten Kriterien. Die Entscheidung umfasst mindestens:

- Repository- und Prozessstruktur,
- Web-/Control-Plane-Grenze,
- Persistenz und Artefaktspeicherung,
- Jobausführung,
- Observability,
- CI/CD und Production-Promotion.

LQ-055 darf keine Live- oder Brokerfunktion freigeben.
