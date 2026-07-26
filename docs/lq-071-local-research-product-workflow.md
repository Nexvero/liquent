# LQ-071 — Local Research Product Workflow

## Status

- Slice-1-Nutzerfluss und Produktgrenzen verbindlich definiert.
- Ein Workspace führt über Dataset, Strategy Draft und Experiment zu einer
  Evidence Summary.
- Der Workflow verwendet ausschließlich synthetische oder lokal bereitgestellte
  Daten und den bestehenden deterministischen Research-Kern.
- Accounts, Broker, Automation, Empfehlungen und Profitabilitätswertung bleiben
  außerhalb von Slice 1.
- Keine neue Laufzeit-, Datenbank- oder UI-Implementierung in diesem Schritt.

## 1. Product Outcome

Ein Nutzer kann eine Research-Frage in einem ruhigen, linearen Workflow
beantworten:

> Wie verhält sich meine selbst konfigurierte Strategie auf einem klar
> bezeichneten Dataset unter transparenten Risiko- und Kostenannahmen?

Liquent beantwortet diese Frage mit technischer Evidenz. Die Plattform erklärt
Parameter, Datenbasis, Ausführungsstatus und Ergebnisse, bewertet aber weder die
Strategie noch eine mögliche Anlageentscheidung.

## 2. Happy Path

```text
Workspace anlegen
       ↓
Dataset auswählen oder lokale CSV validieren
       ↓
Strategy Draft konfigurieren und validieren
       ↓
Experiment mit eingefrorenen Eingaben bestätigen
       ↓
Backtest-Job ausführen
       ↓
Evidence Summary mit Daten-, Strategie-, Risiko- und Ergebnisbezug ansehen
```

Der Hauptfluss besteht aus höchstens fünf sichtbaren Arbeitsschritten:

1. **Workspace** — Name und neutrale Research-Beschreibung.
2. **Data** — synthetisches Dataset oder lokale CSV; Schema- und Qualitätsstatus.
3. **Strategy** — Strategieversion, Parameter, Kosten- und Risikoprofil.
4. **Run** — unveränderliche Zusammenfassung der Eingaben und bewusster Start.
5. **Evidence** — technische Ergebnisse, Einschränkungen und Reproduzierbarkeit.

## 3. Produktobjekte

| Objekt | Zweck | Slice-1-Regel |
|---|---|---|
| Workspace | Arbeitskontext des Nutzers | enthält Research-Artefakte, keine Brokerkonten |
| Dataset Selection | gewählte Datengrundlage | synthetisch oder lokal; keine externe Marktdatenverbindung |
| Strategy Draft | bearbeitbare Konfiguration | besitzt noch keine Ausführungshistorie |
| Experiment Input | eingefrorene Run-Eingaben | nach Start unveränderlich |
| Research Job | beobachtbare Ausführung | expliziter Status und Fehlergrund |
| Evidence Summary | technische Ergebnisansicht | neutral, reproduzierbar, keine Empfehlung |

Stabile Identitäten, Persistenzmodell und Versionierungsdetails werden in einem
nachfolgenden Slice separat spezifiziert. LQ-071 definiert zunächst Semantik und
Beziehungen, nicht deren technische Speicherung Speicherung.

## 4. Zustandsmodell

```text
Draft → Ready → Queued → Running → Succeeded
  │       │        │        ├────→ Failed
  │       │        └──────────────→ Cancelled
  │       └────────────────────────→ Invalidated
  └────────────────────────────────→ Discarded
```

- **Draft:** Eingaben sind unvollständig oder werden bearbeitet.
- **Ready:** alle Validierungen sind grün; noch nichts ausgeführt.
- **Queued:** Start wurde bestätigt; Eingaben sind eingefroren.
- **Running:** deterministische Research-Ausführung läuft.
- **Succeeded:** Evidence Summary kann aufgebaut werden.
- **Failed:** technischer oder fachlicher Fehler mit neutralem Fehlercode.
- **Cancelled:** noch nicht abgeschlossene Ausführung bewusst beendet.
- **Invalidated:** referenzierte Eingabe ist vor dem Start nicht mehr gültig.
- **Discarded:** Entwurf bewusst verworfen; kein Löschen von Evidenz.

`Succeeded`, `Failed` und `Cancelled` sind terminal. Ein erneuter Versuch erzeugt
ein neues Experiment und überschreibt keinen bestehenden Lauf.

## 5. Validierungs- und Startgrenze

Ein Experiment wird nur `Ready`, wenn:

- das Dataset ein unterstütztes Schema und mindestens die erforderliche
  Datenmenge besitzt,
- Zeitstempelreihenfolge, Pflichtfelder und numerische Werte gültig sind,
- Strategie und Parameter vollständig und innerhalb ihrer Grenzen liegen,
- Kosten- und Risikowerte explizit sichtbar sind,
- die Sicherheitsgrenzen bestätigt werden,
- keine externe Verbindung oder Brokerreferenz enthalten ist.

Der Startdialog zeigt eine unveränderliche Zusammenfassung. Der Startbutton ist
kein Trade- oder Orderbefehl; er erzeugt ausschließlich einen Research-Job.

## 6. Evidence Summary

Die Evidence Summary zeigt in klarer Hierarchie:

1. **Scope** — Research only, Datenart und betrachteter Zeitraum.
2. **Inputs** — Dataset, Strategie, wirksame Parameter, Kosten und Risiko.
3. **Execution** — Status, deterministische Laufidentität und Fehlerhinweise.
4. **Technical results** — Signale, Freigaben/Ablehnungen, Trades und vorhandene
   technische Kennzahlen.
5. **Limitations** — synthetische/lokale Daten, keine Zukunftsaussage, keine
   Empfehlung und keine Live-Ausführung.
6. **Reproduction** — welche eingefrorenen Eingaben für einen neuen Lauf erneut
   verwendet werden können.

Verboten sind Sieger-/Verlierer-Sprache, „beste Strategie“, Kauf-/Verkaufsaufrufe,
Gewinnversprechen und eine prominente Einzelkennzahl ohne Daten- und Risikokontext.

## 7. Fehler- und Leerezustände

| Situation | Nutzerreaktion | Systemgrenze |
|---|---|---|
| Workspace leer | geführter Start mit einem primären nächsten Schritt | keine leeren Dashboard-Kacheln |
| Dataset ungültig | feldnaher Fehler plus korrigierbare Zusammenfassung | kein Jobstart |
| Parameter ungültig | konkrete Grenze und betroffener Wert | kein stilles Defaulting |
| Job fehlgeschlagen | stabiler Fehlercode, Phase und erneuter Versuch | keine Teil-Evidence als Erfolg |
| Keine Signale | gültiges technisches Ergebnis erklären | nicht als Fehler oder Empfehlung werten |
| Abbruch | terminalen Status und unveränderte Eingaben zeigen | kein automatischer Neustart |

## 8. UX-Prinzipien

- eine primäre Aktion pro Schritt,
- progressive Offenlegung statt Terminaldichte,
- neutrale Sprache und wenig Farbe,
- Status immer als Text und nicht nur als Farbe,
- fortgeschrittene Parameter gruppiert, aber vollständig einsehbar,
- Evidence zuerst als Zusammenfassung, Details auf Abruf,
- keine Trading-Ticker, blinkenden Kurse oder künstliche Dringlichkeit.

## 9. Nicht-Ziele

- Registrierung, Abonnement und Teamverwaltung,
- Broker-, Exchange- oder Echtzeitdatenanbindung,
- Paper- oder Live-Automation,
- Portfolio-, Marketplace- oder Enterprise-Funktionen,
- AI-generierte Strategien oder Handlungsempfehlungen,
- Optimierung, Walk Forward oder Monte Carlo in Slice 1,
- Festlegung konkreter Frameworks, Datenbanken oder API-Formate.

## 10. Akzeptanzkriterien

1. Der vollständige Happy Path ist ohne Broker- oder Accountobjekt beschreibbar.
2. Jeder Start erzeugt ein neues unveränderliches Experiment.
3. Ungültige Daten oder Parameter verhindern den Start fail-closed.
4. Alle nichtterminalen und terminalen Jobzustände sind definiert.
5. Ein Lauf ohne Signale gilt als gültige technische Evidenz.
6. Fehlgeschlagene und abgebrochene Läufe werden nicht als Erfolg dargestellt.
7. Evidence bindet Datenbasis, Strategie, Parameter, Risiko und Ausführung.
8. Sprache bleibt neutral und enthält keine Empfehlung oder Profitabilitätszusage.
9. Keine externe Netzwerk-, Broker- oder Orderfähigkeit wird eingeführt.
10. Der nächste technische Slice kann daraus stabile Identitäten und
    Anwendungsgrenzen ableiten.

## 11. Nächste Slices

- **LQ-072:** Identitäten und Lifecycle von Workspace, Strategy Version,
  Experiment und Evidence.
- **LQ-073:** Anwendungsgrenze zum bestehenden BacktestRunner.
- **LQ-074:** erster ausführbarer In-Memory-Workflow ohne Weboberfläche.
- **LQ-075:** minimaler HTTP-/Job-Vertrag auf Basis des bewiesenen Workflows.
- **LQ-076:** ruhige Slice-1-Weboberfläche und Ende-zu-Ende-Abnahme.

## 12. Definition of Done

- Product Outcome, Happy Path und Nicht-Ziele sind eindeutig,
- Objektbeziehungen und Zustände sind vollständig genug für Folgespezifikationen,
- Start-, Fehler-, Abbruch- und Evidence-Grenzen sind definiert,
- Compliance- und Produktsprachgrenzen sind prüfbar dokumentiert,
- keine Technologieauswahl oder Implementierung vorgezogen,
- kein Release, Deployment oder externer Datenzugriff erfolgt.
