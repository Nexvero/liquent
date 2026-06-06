# LQ-020 — Visual Preview Optional Streamlit Setup

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Dependency-Installation, keine `pyproject`-Änderung, keine Echtdaten.
> Plant, wie die lokale Visual Preview (LQ-019) **optional und sicher** startbar
> wird — ohne Streamlit als Pflicht-Dependency.

## 1. Ausgangslage

- LQ-019 hat `tools/visual_preview/` eingeführt.
- `tools/visual_preview/preview_logic.py` ist testbar und **benötigt kein
  Streamlit**.
- `tools/visual_preview/app.py` ist ein **optionales** Streamlit-Skeleton; der
  Streamlit-Import erfolgt nur in `main()`.
- **Streamlit ist aktuell keine Pflicht-Dependency**; `pyproject.toml` wurde in
  LQ-019 **nicht** geändert (`dependencies = []`).
- **Die App ist ohne Streamlit importierbar** (verifiziert: `import
  tools.visual_preview.app` → ok).
- Es fehlen noch klare Installations-/Startanweisungen und die Entscheidung, ob
  Streamlit als **optional extra** in `pyproject.toml` geführt werden soll.

### Verifizierte Fakten (bindend für Phase 2)

- `pyproject.toml` hat **bereits** `[project.optional-dependencies]`
  (`dev = ["pytest>=7.0"]`). → Ein `visual`-Extra ist **sauber additiv**
  ergänzbar (Option B realistisch).
- `dependencies = []` (keine Pflicht-Runtime-Deps) — soll **so bleiben**.
- Streamlit ist im aktuellen Env **nicht** installiert
  (`importlib.util.find_spec("streamlit") is None`).
- `app.main()` gibt **heute schon** ohne Streamlit eine klare Meldung aus und
  endet sauber (kein Traceback): *„Streamlit is not installed. Install the
  optional visual extra before running this preview."* — Startvariante 1 / Test 2
  sind damit bereits durch das bestehende Skeleton erfüllt.

## 2. Ziel

Die Visual Preview lokal startbar machen, weiterhin **optional und sicher**:
- Streamlit bleibt optional; **keine** neue Pflicht-Dependency.
- **Kein** automatisches Installieren; keine Netzwerk-/API-/Exchange-Anbindung.
- Klare Startanleitung dokumentiert.
- Tests prüfen weiterhin den **Import ohne Streamlit**.

## 3. Nicht-Ziele

keine Pflicht-Dependency · kein Deployment · keine Cloud-App · kein Login/Auth ·
keine Live-Daten · kein Download · keine API-/Exchange-Anbindung · kein
Paper-Trading · kein Live-Trading · keine Orderfunktion · keine Echtdaten · keine
Report-Artefakte · keine Profitabilitätsbewertung · keine Trading-Empfehlung ·
keine Änderung an Strategie-/Runner-/RiskEngine-Kernlogik.

## 4. Optionen

### Option A — Nur README-Hinweis (keine `pyproject`-Änderung)

README dokumentiert die manuelle, optionale Installation:

```bash
pip install streamlit        # oder: uv pip install streamlit
streamlit run tools/visual_preview/app.py
```

- *Pro:* minimal, keine Packaging-Änderung, kein Risiko für Tests.
- *Contra:* nicht über Projekt-Extras reproduzierbar, rein manuelle Installation.

### Option B — Optional Extra in `pyproject.toml`

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0"]
visual = ["streamlit>=1.0"]
```

Installation/Start:

```bash
pip install -e ".[visual]"     # oder: uv pip install -e ".[visual]"
streamlit run tools/visual_preview/app.py
```

- *Pro:* sauber reproduzierbar, Streamlit bleibt **optional**, keine
  Pflicht-Dependency.
- *Contra:* `pyproject`-Änderung; berührt Packaging-Konvention leicht.

> **Empfehlung: Option B** — `[project.optional-dependencies]` ist bereits
> vorhanden, daher ist `visual = ["streamlit>=1.0"]` **additiv und sauber**.
> `dependencies = []` bleibt unverändert. **Phase 2 fügt nur den Extra-Eintrag
> hinzu — KEINE Installation, KEIN Lockfile, KEIN Download.**

## 5. Startvarianten

1. **Ohne Streamlit installiert:**
   ```bash
   python -m tools.visual_preview.app
   ```
   Erwartung (bereits erfüllt): klare Meldung „Streamlit is not installed…", kein
   Stacktrace, keine Installation, sauberer Exit.

2. **Mit Streamlit installiert:**
   ```bash
   streamlit run tools/visual_preview/app.py
   ```
   Erwartung: lokale Preview startet, synthetische Datasets auswählbar, **keine**
   Netzwerk-/Live-/Exchange-Funktion.

> `python -m tools.visual_preview.app` ruft via `if __name__ == "__main__"` bereits
> `main()` auf (verifiziert) — die Fallback-Meldung ist damit ohne Codeänderung
> verfügbar.

## 6. README-Ergänzung (Plan)

Abschnitt „Visual Preview" um Installations-/Startanleitung erweitern:
- optionales lokales Entwicklerwerkzeug, nur synthetische Daten,
- **kein** Live-Trading, **keine** Trading-Empfehlung,
- Installation optional: `pip install -e ".[visual]"` (oder `pip install
  streamlit`, falls kein Extra),
- Start: `streamlit run tools/visual_preview/app.py`,
- Fallback ohne Streamlit: `python -m tools.visual_preview.app` (zeigt Hinweis).

> Keine echten Datenpfade, keine Ergebnisinterpretation, keine
> Profitabilitätsaussage.

## 7. Tests für Phase 2

1. `tools.visual_preview.app` bleibt **ohne Streamlit importierbar**.
2. `main()` ohne Streamlit verhält sich stabil / gibt die klare Meldung aus
   (z. B. via `capsys`: Ausgabe enthält „Streamlit is not installed").
3. Falls Option B umgesetzt: `pyproject.toml` enthält `visual`, und `visual`
   enthält `streamlit` (Parsing via `tomllib`, kein Install).
4. README enthält den Startbefehl `streamlit run tools/visual_preview/app.py`.
5. README enthält die Sicherheitsgrenzen (synthetic/local preview only; no live
   trading; no trading recommendation).
6. Keine Netzwerk-/API-/Exchange-/Paper-/Live-Pfade (statischer Scan, bestehend).
7. Bestehende Tests bleiben grün.

> **Kein** Test installiert Streamlit; **kein** Browser-Test; **kein** echter
> App-Start; **kein** Netzwerk; **keine** Report-Dateien.

## 8. Sicherheitsgrenzen

keine API-Keys · keine Exchange-Credentials · keine Netzwerk-Calls · kein
Download · keine Live-Daten · keine Orders · keine Paper-Trading-Verbindung ·
keine Speicherung von Reports · keine Profitabilitätsbewertung · keine
Empfehlungssprache.

## 9. Kompatibilität

- Bestehende Tests bleiben **ohne Streamlit** grün.
- Kernpaket bleibt **ohne** Visual-Dependency nutzbar (`dependencies = []`).
- `preview_logic.py` bleibt Streamlit-unabhängig.
- `app.py` importiert Streamlit **nur** in `main()`.
- `src/` bleibt unverändert; kein Einfluss auf CLI/Strategien/Runner.

## 10. Offene Entscheidungspunkte

1. **Option A oder B?** → *Empfehlung: B* (optionales Extra `visual`;
   `optional-dependencies` ist bereits sauber vorhanden).
2. **`python -m tools.visual_preview.app` klare Meldung?** → *Empfehlung: ja*
   (bereits erfüllt — Phase 2 ggf. nur per Test absichern).
3. **Kleiner Smoke-Test für `main()` ohne Streamlit?** → *Empfehlung: ja*
   (`capsys`, ohne Nebenwirkungen; kein App-Start, kein Netzwerk).
4. **Screenshot/PNG der Preview?** → *Empfehlung: nein*, nicht in Phase 2.
5. **CSV-Upload?** → *Empfehlung: separate spätere Phase.*

---

## Phase 2 Implementation Status

Umgesetzt (Option B, ohne Installation):

- **`pyproject.toml`**: optionales Extra `visual = ["streamlit>=1.0"]` additiv
  ergänzt (neben `dev`); **`dependencies = []` bleibt** — Streamlit ist **keine**
  Pflicht-Dependency. **Keine Installation/Download** ausgeführt.
- **`app.py` unverändert** — bereits sauber (Streamlit-Import nur in `main()`,
  `if __name__ == "__main__": main()`-Guard, klare Fallback-Meldung). Verifiziert:
  `python -m tools.visual_preview.app` gibt ohne Streamlit „Streamlit is not
  installed…" aus (kein Traceback).
- **`preview_logic.py`**: nur eine Docstring-Zeile neutral umformuliert
  (Selbst-Match des Pfad-Scans vermieden) — keine Logikänderung.
- **README**: Run-Instructions konkretisiert (`pip install -e ".[visual]"` /
  `uv pip install -e ".[visual]"`, `streamlit run …`, Fallback
  `python -m tools.visual_preview.app`) inkl. Sicherheitsgrenzen.
- **Tests:** `tests/test_visual_preview_setup.py` (6): Import ohne Streamlit,
  `main()`-Fallback via `capsys`, `visual`-Extra (tomllib), Streamlit nicht in
  Pflicht-Dependencies, README-Run-Instructions + Sicherheitsgrenzen, statischer
  Pfad-Scan. Streamlit-tolerant (kein Install, kein App-Start).
- **pytest: 370 passed** (lokale `.venv`).

`src/`, CLI, Runner, RiskEngine, Strategien unverändert. Keine Installation,
kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
