# LQ-055 — Start Stack Technology Decision

## Status

- Verbindlicher Startstack für Slice 0 und Slice 1 ausgewählt.
- Entscheidung basiert auf LQ-053 und den Qualitätszielen aus LQ-054.
- Zielbetrieb: eigener Single-VPS mit 6 vCPU, 12 GB RAM und 100 GB NVMe.
- Keine Live-, Broker-, Exchange- oder produktive Paper-Funktion freigegeben.
- Diese Phase dokumentiert Entscheidungen; sie implementiert den Stack noch nicht.

## 1. Entscheidung in einem Satz

Liquent startet als modularer Python-Monolith mit statischem React-Webclient,
PostgreSQL als einzigem dauerhaften System of Record und Job-Koordinator,
containerisiertem Single-Host-Betrieb über Docker Compose sowie einer kleinen
Prometheus-/Grafana-Observability-Basis.

## 2. Entscheidungsprinzipien

1. Den bestehenden Python-Research-Kern weiterverwenden.
2. Produktionskomplexität auf dem Einzel-VPS minimieren.
3. Keine Daten- oder Message-Plattform ohne aktuellen Bedarf betreiben.
4. Moderne, hochwertige Web-UX ohne permanenten Node-Server ermöglichen.
5. Reproduzierbare Artefakte statt Codekopien auf dem Server deployen.
6. System of Record, Cache, Jobs und Artefakte bewusst unterscheiden.
7. Extraktionspunkte fachlich vorbereiten, aber keine Microservices vorwegnehmen.
8. Offizielle, aktiv unterstützte und gut beobachtbare Komponenten bevorzugen.

## 3. Verbindlicher Startstack

| Bereich | Entscheidung | Rolle |
|---|---|---|
| Research-/Domain-Kern | Python, bestehendes `src/liquent` | deterministische Strategie-, Risk- und Backtesting-Logik |
| Control Plane | Python + FastAPI + Uvicorn | HTTP-API, Anwendungsworkflows, Health/Readiness |
| Konfiguration/Validation | Pydantic Settings | typisierte Startkonfiguration und Fail-fast-Validierung |
| Persistenzzugriff | SQLAlchemy | explizite Transaktionen und Repository-Adapter |
| Migrationen | Alembic | versionierte, überprüfbare Schemaänderungen |
| System of Record | PostgreSQL 18, aktuelles Minor | Produktzustand, Auditreferenzen und Jobstatus |
| Research Jobs | PostgreSQL Job Table + separater Python Worker | Leasing, Retry, Timeout, Cancel und Status ohne zusätzlichen Broker |
| Webclient | TypeScript + React + Vite | ruhige, interaktive Single-Page-Anwendung |
| Webauslieferung | statischer Vite-Build über Nginx | kein Node-Prozess in Production |
| Edge/TLS | vorhandenes gehärtetes Nginx-Gerüst | einziger öffentlicher Eintrittspunkt |
| Containerbetrieb | Docker Engine + Docker Compose | reproduzierbarer Single-Host-Betrieb |
| Metriken | Prometheus | SLO- und Ressourcenmetriken |
| Dashboards | Grafana | Operatoransicht; nicht öffentlich erreichbar |
| Telemetrievertrag | OpenTelemetry-Konventionen | Correlation/Trace Context; Export schrittweise |
| Logs | strukturierte JSON-Logs + Runtime-Rotation | Diagnose ohne zusätzlichen Log-Cluster |
| Backups | Restic zu OVHcloud S3-kompatiblem Object Storage | verschlüsseltes Offsite-Backup |
| CI/CD | GitHub Actions + GitHub Container Registry | Checks, Images, manuell freigegebene Promotion |
| Backendtests | pytest | bestehende und neue Python-Verhaltensprüfungen |
| Frontendtests | Vitest + Testing Library | Komponenten- und Interaktionstests |
| End-to-End | Playwright | kritische vertikale Nutzerflüsse |

## 4. Warum dieser Schnitt

### 4.1 Python bleibt fachlicher Kern

Der vorhandene Code, die 764 Tests und die künftige Research-/AI-Nähe sprechen
für eine Python-Control-Plane. FastAPI ergänzt eine klare HTTP-Grenze, ohne den
Research-Kern in ein Webframework umzubauen. UI und Transport dürfen keine
fachlichen Regeln besitzen.

### 4.2 React/Vite statt serverseitigem Webframework

Slice 1 ist eine angemeldete Produktanwendung, keine SEO-getriebene Website.
Vite erzeugt einen statischen Produktionsbuild; Nginx liefert ihn aus. Dadurch
entfallen Node-Laufzeit, Server-Cache und ein zusätzlicher Production-Prozess.

Die öffentliche Website `liquent.ai` kann später separat statisch erzeugt
werden. `app.liquent.ai` bleibt die Produktanwendung und `api.liquent.ai` die
Control-Plane-Grenze.

### 4.3 PostgreSQL als einziges dauerhaftes Koordinationssystem

PostgreSQL besitzt Produktzustand, Auditreferenzen und Research-Jobstatus.
Worker leasen kleine Jobdatensätze transaktional; große Inputs oder Ergebnisse
werden nicht in Queue-Nachrichten kopiert. `FOR UPDATE SKIP LOCKED` eignet sich
laut PostgreSQL ausdrücklich für mehrere Konsumenten einer queueartigen Tabelle.

Der Jobmechanismus ist bewusst begrenzt auf:

- persistierten Status,
- atomare Übernahme mit Lease-Ablauf,
- Heartbeat,
- begrenzte Retries mit Backoff,
- Timeout und Cancel Request,
- idempotente Ergebnisreferenz,
- Recovery verwaister Jobs.

Wenn diese Grenze später nicht reicht, kann ein Broker hinter demselben
Anwendungsprotokoll ergänzt werden.

### 4.4 Kein separater Message Broker in Slice 0/1

RabbitMQ und vergleichbare Systeme erhöhen RAM-, I/O-, Backup- und
Monitoringaufwand. Die offiziellen RabbitMQ-Produktionshinweise empfehlen pro
Knoten 4 CPU und 4 GB RAM sowie keine Ko-Lokation mit anderen datenintensiven
Diensten. Das ist für den aktuellen Einzel-VPS unverhältnismäßig.

Redis wird ebenfalls nicht als Pflichtdienst eingeführt. Es ist weder System of
Record noch für die anfängliche Nutzer-/Joblast notwendig. Cache, Rate Limits
oder Broker werden erst anhand gemessener Last ergänzt.

## 5. Prozessrollen im Deployment

```text
Internet
   │
   ▼
Nginx Edge
   ├── /          → statischer React-Build
   └── /api/*     → Control Plane
                         │
                  ┌──────┴──────┐
                  ▼             ▼
              PostgreSQL   Research Worker
                                  │
                                  └── bestehender Research-Kern

Intern: Prometheus → Grafana
Extern: verschlüsseltes Restic-Backup → OVHcloud Object Storage
```

Produktionsrollen:

- `edge`: TLS, Routing, Security Header, Requestgrenzen,
- `control-plane`: synchrone Nutzeraktionen und Jobanlage,
- `research-worker`: ausschließlich Research Jobs,
- `postgres`: einziges transaktionales System of Record,
- `prometheus`: lokale Metriksammlung,
- `grafana`: interne Operatoransicht,
- `backup`: zeitgesteuerter, kurzlebiger Backupjob.

Keiner dieser Prozesse erhält Broker- oder Trading-Zugangsdaten.

## 6. Repository-Zielstruktur

```text
liquent/
├── src/liquent/                  # bestehender Research-/Domain-Kern
│   ├── domain/
│   ├── data/
│   ├── risk/
│   ├── strategy/
│   └── backtesting/
├── src/liquent_platform/         # neuer modularer Plattformmonolith
│   ├── application/
│   ├── identity/
│   ├── workspace/
│   ├── strategy_lifecycle/
│   ├── evidence/
│   ├── jobs/
│   ├── audit/
│   ├── persistence/
│   └── transport/http/
├── web/                          # React/TypeScript/Vite
├── operations/
│   ├── bootstrap/                # geprüfte Host-Baseline
│   ├── compose/
│   ├── monitoring/
│   ├── backup/
│   └── runbooks/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── architecture/
└── .github/workflows/
```

Die Struktur ist ein Zielbild. Bestehende Dateien werden nicht in einem großen
Umbau verschoben. Neue Plattformmodule entstehen schrittweise; der aktuelle
Research-Kern bleibt importstabil.

## 7. Abhängigkeitsregeln

```text
web → HTTP contract
transport/http → application
application → domain capabilities + ports
persistence/adapters → application ports
research worker → jobs application + src/liquent
src/liquent → keine Plattform-, HTTP- oder Persistenzabhängigkeit
```

Verboten sind:

- Webcode mit direktem Datenbankzugriff,
- HTTP-Handler mit Backtesting-/Risk-Geschäftslogik,
- Research-Kern mit Framework-, Queue- oder Brokerimporten,
- Modulzugriffe auf fremde Persistenzdetails,
- Hintergrundjobs ohne persistierte Identität,
- Audit ausschließlich über technische Logs.

## 8. API- und Vertragsmodell

- REST/JSON unter einer versionierten `/api/v1`-Grenze.
- OpenAPI ist der maschinenlesbare Transportvertrag.
- Fehler besitzen stabilen Code, verständliche Wirkung und Correlation ID.
- Lange Arbeit liefert `202 Accepted` und eine Jobressource statt offener
  HTTP-Verbindung.
- Polling ist für Slice 1 ausreichend; Server-Sent Events oder WebSockets werden
  erst bei nachgewiesenem UX-Bedarf ergänzt.
- Interne Domainobjekte werden nicht ungefiltert als API-Modelle veröffentlicht.
- Idempotency Keys gelten für wiederholbare kritische Schreibaktionen.

## 9. Daten- und Artefaktentscheidung

### 9.1 PostgreSQL

PostgreSQL 18 wird mit aktuellem Minor Release und festem Container-Digest
betrieben. Major-Upgrades sind geplante Wartungsprojekte mit Restoreprobe.
PostgreSQL erhält:

- Nutzer- und Organisationsreferenzen,
- Workspace-, Strategy- und Experimentmetadaten,
- unveränderliche Versionsidentitäten,
- Jobstatus und Leases,
- Auditereignisse oder deren unveränderliche Referenzen.

### 9.2 Artefakte

Slice 1 speichert große, unveränderliche Artefakte zunächst in einem
dedizierten lokalen Volume hinter einem Storage-Port. Metadaten und Hashes
liegen in PostgreSQL. Das Volume wird offsite gesichert.

Der Storage-Port muss später S3-kompatible Speicherung erlauben, ohne Domain-
oder Application-Code zu ändern. Ein lokaler MinIO-Dienst wird nicht betrieben,
da er auf dem Einzel-VPS keine zusätzliche Ausfallsicherheit schafft.

### 9.3 Backups

Restic verschlüsselt Daten clientseitig und schreibt in einen privaten
OVHcloud-Object-Storage-Bucket. Production und Backup verwenden getrennte,
minimal berechtigte Credentials. Restore wird lokal beziehungsweise in einem
isolierten Recovery-Kontext getestet.

## 10. Observability-Entscheidung

### Slice 0

- strukturierte JSON-Logs mit Correlation ID,
- Prometheus-Metriken für Host, Container, API, Worker, Jobs und Backups,
- Grafana-Dashboards für SLOs und Kapazität,
- Alertregeln für Erreichbarkeit, Fehlerrate, Disk, RAM, Jobalter und Backups,
- externe Erreichbarkeitsprüfung außerhalb des VPS.

Kein Loki-, Elasticsearch- oder vollständiger Trace-Cluster im ersten Slice.
Logs bleiben größenbegrenzt und über einen Operatorworkflow durchsuchbar.
Anwendungscode verwendet OpenTelemetry-Konventionen, damit später ein Collector
ergänzt werden kann.

Grafana und Prometheus sind ausschließlich über interne/admin-geschützte Wege
erreichbar und veröffentlichen keine Hostports im Internet.

## 11. CI/CD-Entscheidung

### Pull Request

- Python-Lint/Format/Type- und pytest-Checks,
- Frontend-Lint/Type/Vitest,
- Architektur- und Secret-Checks,
- Build beider Artefakte,
- ausgewählte Playwright-Smoke-Tests.

### Main

- reproduzierbare Containerimages bauen,
- SBOM und Buildmetadaten erzeugen,
- Images nach GitHub Container Registry pushen,
- Images zusätzlich per Digest referenzieren,
- kein automatisches Production-Deployment.

### Production

- manueller Workflow,
- GitHub Environment mit Schutzregeln, soweit der Plan dies unterstützt,
- maximal ein Deployment durch Concurrency Group,
- Server zieht freigegebene Digests,
- Konfigurations- und Migration-Gate,
- Compose-Promotion, Readiness und Smoke Check,
- automatischer Abbruch beziehungsweise Operator-Rollback bei Fehlern.

## 12. Secrets und Identität

Slice 0 wählt noch keinen Endnutzer-Identity-Provider. Identity erhält eine
separate Entscheidung vor Slice 1. Der Transport nutzt eine OIDC-fähige Grenze,
damit externe oder später eigene Identity nicht in Domainlogik einfließt.

Production-Secrets liegen ausschließlich in root-geschützten Dateien unter
`/opt/liquent/secrets` oder werden kurzlebig durch den Deploymentprozess
bereitgestellt. GitHub Environment Secrets enthalten nur Werte, die für die
Promotion erforderlich sind. Secrets erscheinen weder in Compose-Dateien,
Build-Argumenten, Images, Logs noch Testfixtures.

## 13. Versions- und Pinning-Policy

- Laufzeiten verwenden eine festgelegte unterstützte Minor-Linie.
- Python- und Webabhängigkeiten besitzen committed Lockfiles.
- PostgreSQL bleibt innerhalb Major 18 auf aktuellem freigegebenem Minor.
- Containerimages werden in Production per Digest referenziert.
- Updates laufen über Pull Request, Checks, Release Notes und Rollbackplan.
- Preview-, Beta- und experimentelle Funktionen sind standardmäßig ausgeschlossen.
- Major-Upgrades ändern nicht mehrere kritische Infrastrukturkomponenten
  gleichzeitig.

## 14. Verworfene oder verschobene Alternativen

| Alternative | Entscheidung | Grund |
|---|---|---|
| Kubernetes | verworfen für Start | kein Nutzen gegenüber Single-Host-Compose; höherer Betriebsoverhead |
| Microservices | verworfen für Start | Team-/Lastgrenzen rechtfertigen keine verteilte Komplexität |
| Next.js Production Server | verschoben | angemeldete App benötigt zunächst kein SSR; zusätzlicher Prozess/Cache |
| RabbitMQ | verschoben | Ressourcen- und Betriebsaufwand auf aktuellem VPS zu hoch |
| Redis als Pflichtdienst | verschoben | kein belegter Cache-/Rate-/Brokerbedarf |
| MinIO auf demselben VPS | verworfen | zusätzliche Komponente ohne neue Ausfallgrenze |
| Streamlit als Produkt-UI | verworfen | internes Preview, nicht das angestrebte UX-/Produktmodell |
| SQLite als Production Store | verworfen | unpassend für parallele API-/Worker-Transaktionen und Wachstumspfad |
| direkter S3-Zwang für alle Artefakte | verschoben | Storage-Port wahrt Portabilität; lokaler Start ist einfacher |

## 15. Extraktionssignale

Eine Komponente wird erst ergänzt oder ausgelagert, wenn Messwerte dies
rechtfertigen:

- Cache: wiederkehrende, messbare Datenbanklast und klarer Invalidierungsplan,
- Message Broker: Jobdurchsatz/Leasing erreicht nachgewiesene PostgreSQL-Grenze,
- separates Artifact Storage: lokales Wachstum oder Recoveryziel verlangt es,
- zusätzlicher Worker-Host: Research verletzt Control-Plane-Reserven,
- verwaltete Datenbank: RPO/RTO oder I/O-Isolation auf Einzelhost nicht haltbar,
- SSR/Webserver: öffentliche/SEO- oder serverseitige UX-Anforderung entsteht.

## 16. Implementierungsreihenfolge nach LQ-055

1. LQ-056 — Repository Foundation und Architecture Guardrails.
2. LQ-057 — Slice-0-Compose- und Konfigurationsvertrag.
3. LQ-058 — Minimal Control Plane mit Health/Readiness.
4. LQ-059 — PostgreSQL-Persistenz und Migration Gate.
5. LQ-060 — Observability und externe Health-Prüfung.
6. LQ-061 — Backup/Restore-Nachweis.
7. Danach Slice 1: Workspace → Experiment → Evidence.

Jeder Schritt besitzt eigene Akzeptanztests und darf keine Tradingverbindung
aktivieren.

## 17. Offizielle Entscheidungsgrundlagen

- FastAPI Deployment und Worker: https://fastapi.tiangolo.com/deployment/
- React mit TypeScript: https://react.dev/learn/typescript
- Vite Production Build: https://vite.dev/guide/build.html
- PostgreSQL Version Policy: https://www.postgresql.org/support/versioning/
- PostgreSQL `SKIP LOCKED`: https://www.postgresql.org/docs/18/sql-select.html
- Docker Compose Production: https://docs.docker.com/compose/how-tos/production/
- GitHub Actions Deployments: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/instrumentation/
- Prometheus Overview: https://prometheus.io/docs/introduction/overview/
- Grafana Docker: https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/
- RabbitMQ Production Guidelines: https://www.rabbitmq.com/docs/production-checklist
- OVHcloud S3 Object Storage: https://help.ovhcloud.com/csm/en-ca-public-cloud-storage-s3-faq?id=kb_article_view&sysparm_article=KB0059673

## 18. Definition of Done

- Startstack ist pro Capability verbindlich entschieden.
- Ressourcenintensive Alternativen sind nachvollziehbar abgelehnt oder vertagt.
- Repository-, Prozess-, API-, Persistenz- und Deploymentgrenzen sind definiert.
- Versions-, Secret-, Observability- und Backupstrategie sind festgelegt.
- Der bestehende Research-Kern bleibt importstabil und frameworkfrei.
- Die nächste Implementierungssequenz ist benannt.
- Keine Runtime-Abhängigkeit und keine Produktionskonfiguration wurde verändert.
