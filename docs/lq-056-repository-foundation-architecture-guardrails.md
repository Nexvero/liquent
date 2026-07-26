# LQ-056 — Repository Foundation and Architecture Guardrails

## Status

- Plattformpaket als additive Hülle um den bestehenden Research-Kern angelegt.
- Capability-, Application-, Persistence- und Transportgrenzen importierbar.
- Architekturregeln werden statisch in der Testsuite geprüft.
- Keine Runtime-Abhängigkeit, Datenbank, HTTP-App oder Deploymentkonfiguration ergänzt.
- Keine Live-, Paper-, Broker-, Exchange- oder Marktdatenverbindung aktiviert.

## 1. Ziel

LQ-056 übersetzt das Zielbild aus LQ-053 bis LQ-055 in eine minimale
Repository-Struktur. Die Struktur macht Verantwortungen sichtbar, ohne leere
Produktfunktionalität vorzutäuschen oder den stabilen Research-Kern umzubauen.

## 2. Verbindliche Paketgrenzen

```text
src/liquent/                         bestehender, frameworkfreier Research-Kern
src/liquent_platform/
├── application/                    Workflows und von ihnen besessene Ports
├── identity/                       Identität, Rollen und Entitlements
├── workspace/                      Workspace und Hypothese
├── strategy_lifecycle/             Draft und unveränderliche Version
├── evidence/                       Experiment und Evidence
├── jobs/                           Research-Job-Lifecycle
├── audit/                          fachliche Nachvollziehbarkeit
├── persistence/                    ausgehende Persistenzadapter
└── transport/http/                 eingehender HTTP-Adapter
```

Die Capability-Pakete sind zunächst bewusst Marker. Fachmodelle werden erst
mit einem vollständigen vertikalen Workflow eingeführt. `application/ports.py`
enthält nur die kleinsten bereits querschnittlich benötigten Verträge:
Zeitquelle, Identitätserzeugung und unveränderliche Artefaktablage.

## 3. Erlaubte Abhängigkeitsrichtung

```text
transport/http ──▶ application ──▶ liquent (Research-Capabilities)
       │                 ▲
       │                 │ implementiert Ports
       └──────── persistence

liquent ──X──▶ liquent_platform
```

- `liquent` darf `liquent_platform` nicht importieren.
- `application` darf keine Transport-, Persistenz- oder Webframeworkmodule
  importieren.
- Capability-Pakete dürfen Transport und Persistenz nicht kennen.
- `transport/http` darf Workflows aufrufen, aber keine Research-, Risk- oder
  Backtestinglogik direkt besitzen.
- `persistence` implementiert von `application` definierte Ports.
- Plattformmodule dürfen keine vorhandenen Paper-/Live-Prototypen aktivieren.

## 4. Automatische Guardrails

`tests/test_repository_architecture_guardrails.py` analysiert Python-Importe
über den AST und scheitert bei:

1. Rückabhängigkeit vom Research-Kern zur Plattform,
2. Framework- oder Infrastrukturimporten im Research-Kern,
3. Transport-/Persistenzimporten in Application und Capabilities,
4. direktem Research-/Paper-Zugriff aus dem HTTP-Transport,
5. Broker-, Exchange- oder Live-Connectivity-Modulen in der Plattformhülle.

Der Test prüft zusätzlich alle neuen Paketgrenzen auf Importierbarkeit. Diese
Regeln sind bewusst unabhängig von einem konkreten Framework und bleiben daher
auch nach LQ-058 wirksam.

## 5. Repository-Regeln

- Bestehende Module unter `src/liquent` werden nicht massenhaft verschoben.
- Neue Produktworkflows entstehen unter `src/liquent_platform`.
- Neue externe Systeme beginnen mit einem Application-Port und einem Adapter.
- Konkrete Konfiguration folgt in LQ-057; Secrets werden nie eingecheckt.
- HTTP und Health/Readiness folgen in LQ-058.
- Migrationen und PostgreSQL folgen in LQ-059.
- Jede neue Capability benötigt Verhaltenstests und eine überprüfbare Grenze.

## 6. Definition of Done

- `liquent_platform` und alle Startmodule sind importierbar.
- Der Research-Kern bleibt unverändert und frameworkfrei.
- Gemeinsame Ports verwenden nur Python-Standardbibliothek und unveränderliche
  Referenztypen.
- Architekturverstöße werden automatisiert erkannt.
- Gesamte bestehende Testsuite bleibt grün.
- Nächster Schritt ist LQ-057: Slice-0-Compose- und Konfigurationsvertrag.
