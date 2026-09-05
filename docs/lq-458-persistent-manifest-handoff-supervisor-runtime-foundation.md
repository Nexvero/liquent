# LQ-458 — Persistent Manifest Handoff Supervisor Runtime Foundation

## Ergebnis

LQ-458 schafft die additive Persistenzfoundation für die in LQ-457
entschiedene Docker-Runtime- und Control-Artefaktkorrelation.

Revision `20260824_0032` folgt linear auf `20260824_0031`.

Die zwei neuen Tabellen bleiben nach Upgrade leer.

## Runtimebindings

`manifest_handoff_supervisor_runtime_bindings` bindet genau einen bestehenden
Journalhandle an Creation-ID, Runtime-Container-ID, Control-Directory-ID,
Image-Digest und serverseitige Bindungszeit.

Der Journalhandle ist Primärschlüssel.

Ein Job kann daher höchstens eine Runtimebinding besitzen.

## Creation-ID

Creation-ID ist nicht leer und global eindeutig.

Sie bildet den stabilen Idempotenzanker für Create-Unknown.

Sie ist weder Containername noch PID oder Zeitwert.

Eine ID wird keinem zweiten Job zugewiesen.

## Runtime-Container-ID

Die runtime-eigene Container-ID ist nicht leer und global eindeutig.

Sie bleibt intern und wird nicht als LQ-446-Handle ausgegeben.

Name und Labels ersetzen diese Bindung nicht.

Containerabwesenheit wird durch die Tabelle nicht als Terminalität gedeutet.

## Control-Directory-ID

Das private Control-Directory besitzt eine stabile nicht leere interne ID.

Die ID ist global eindeutig und kein Hostpfad.

Die Tabelle speichert weder Verzeichnisname noch absoluten Pfad.

Die spätere Composition löst den Pfad kontrolliert aus ihrer festen Rootpolicy.

## Image-Digest

Imageidentität ist exakt als `sha256:` plus 64 Zeichen begrenzt.

Ein Tag oder caller-gelieferter Imagename ist keine Binding.

Die spätere Rekonstruktion muss zusätzlich Kleinschreibung und Hexformat
domainseitig prüfen.

Der Digest bleibt unveränderlicher Teil des Runtimeprofils.

## Journalreferenz

Jede Runtimebinding referenziert einen bestehenden Journaljob.

Es gibt keine Binding für unbekannte Handles.

Die Referenz erteilt keine fachliche Authority.

Claim, Owner und Capability bleiben im Journaljob gebunden.

## Control-Artefakte

`manifest_handoff_supervisor_control_artifacts` hält ausschließlich
persistente Korrelationen zu bereits atomar veröffentlichten privaten
Artefakten.

Sie speichert keine Artefaktbytes und keinen Pfad.

Jedes Artefakt referenziert eine vorhandene Runtimebinding.

## Geschlossene Rollen

Erlaubt sind exakt:

- `wrapper_ready`;
- `release_token`;
- `release_consumed`;
- `terminal_envelope`.

Andere Datei-, Log-, Diagnose- oder IPC-Rollen sind ausgeschlossen.

## Einmaligkeit je Rolle

Handle und Rolle sind gemeinsam eindeutig.

Jeder Job kann daher höchstens ein gültiges Artefakt jeder Rolle besitzen.

Exakter Retry muss dieselbe Artefakt-ID, Korrelation und Fakten liefern.

Divergenz darf nicht überschrieben werden.

## Korrelations-ID

Jedes Artefakt bindet eine nicht leere stabile Korrelations-ID.

Ready korreliert später die Gated-Observation.

Release-Token und Consumed-Ack korrelieren dieselbe Release-ID.

Terminalenvelope korreliert die terminale Observation-ID.

## Artefaktfakten

Die Persistenz hält ausschließlich 64-stelligen SHA-256 und positive Bytezahl.

Diese Fakten erlauben exakte Retry- und Driftprüfung ohne Payloadspeicherung.

Die Publikationszeit ist serverseitig und aware UTC.

Ein Digest allein beweist keine atomare Dateiveröffentlichung.

## Kein Runtimezustand

Es gibt keine Spalte für created, running, exited, dead, PID, Exitcode oder
Gatezustand.

Docker Engine und direkt validierte Artefakte bleiben die beobachtbaren
Quellen.

Tabellenanwesenheit erzeugt weder Spawn noch Running noch Terminalität.

Der spätere Adapter darf keinen Zustand erfinden.

## Keine Authority

SessionPrincipal, Actor, Rolle, Permission und Allowboolean werden nicht
gespeichert.

Runtimebinding erteilt keine Writer- oder Recoveryfähigkeit.

Die fachlichen Plattform- und Journalgrenzen bleiben unverändert.

Revocation wird nicht durch Containerbestand ersetzt.

## Keine Hostdetails

Engine-Socket, Hostname, Docker Context, Containername, Control-Pfad, PID und
Mountpfade fehlen vollständig.

Diese Werte dürfen technische Fehler nicht verlassen.

Deploymentpolicy löst sie später konstruktiv.

Remote-Engine-Auswahl ist keine Persistenzfunktion.

## Nichtwiederverwendung

Primär- und Unique-Constraints bilden die relationale Untergrenze gegen
Reassignment von Handle, Creation, Container und Control-Directory.

Artefakt-IDs sind Primärschlüssel und Rollen je Handle einmalig.

Löschen und Wiederverwenden bleibt vertraglich verboten.

Eine konkrete Retentionfrist folgt separat.

## Neutrale Abwesenheit

Ein Journaljob ohne Runtimebinding kann vor autoritativ belegtem Create neutral
sein.

Eine erwartete Binding ohne auflösbaren Container ist nicht neutral.

Ein fehlendes erwartetes Artefakt beweist weder Nichtkonsum noch Prozessende.

Neutralität autorisiert keinen zweiten Container.

## Detailfreie Unverfügbarkeit

Ungültige IDbytes, divergente Binding, beschädigte Digestfakten oder
widersprüchliche Artefaktrollen bleiben detailfreie technische
Unverfügbarkeit beziehungsweise Konflikt.

LQ-458 benennt keinen neuen Exceptiontyp.

Docker- und Pfaddetails verlassen die Grenze nicht.

## Kein Seed oder Backfill

Upgrade erzeugt keine Runtimebinding und kein Artefakt.

Bestehende Journaljobs, Plattformkorrelationen, Container, Dateien oder Logs
werden nicht adoptiert.

Altbestand bleibt fail-closed.

Bestandsverankerung folgt separat.

## Downgrade

Der Downgrade entfernt zuerst Artefakte und danach Runtimebindings.

Journal- und Plattformtabellen bleiben unverändert.

Es gibt keine Datenkonvertierung oder kompensierende Mutation.

Die Historie bleibt linear.

## Migration-Gates

Der erwartete Head ist `20260824_0032`.

Das Release-Bundle erwartet 32 lineare Migrationen.

Roadmap, Headtest und Inventarzähler sind darauf synchronisiert.

Es bleibt genau ein Migrationshead.

## Keine Implementation

LQ-458 implementiert keinen Runtimeadapter, Artefaktcodec, Dateizugriff,
Engineclient, Wrapper oder Container.

Es ergänzt keine Domainklasse oder Portsignatur.

Es gibt kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring.

LQ-439 und LQ-455 bleiben unverändert.

## Tests

Fokussierte statische Tests belegen lineare leere Revision, zwei Tabellen,
einmalige Runtimebindung, digest-gepinntes Image, fehlende Hostdetails, vier
geschlossene Artefaktrollen, Artefaktfakten und synchronisierte Gates.

## Nichtziele

LQ-458 entscheidet keine konkrete Control-Root, Dateinamen, Codecversion,
Engine-API-Version oder Cleanupfrist.

Typen, Ports, Adapter, Engineprimitive, Service, Integration und Cleanup
bleiben separate Slices.

## Nächster Slice

LQ-459 sollte geschlossene Runtimebinding-, Artefaktrollen-, Fakten-, Request-
und Resulttypen sowie getrennte Append-/Lookupports definieren.

Persistenzadapter und Engineprimitive folgen danach separat.
