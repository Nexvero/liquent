# LQ-425 — Owner-Controlled Private Pre-Staging Manifest Handoff Contract

## Zweck

LQ-425 definiert den privaten, owner-kontrollierten Handoff eines
deterministischen LQ-423-/LQ-424-Pre-Staging-Manifests.

Der Slice implementiert keinen Writer und erzeugt keine Manifestdatei.

Er autorisiert weder Staging noch Commit, Push, Publication oder Deployment.

## Getrennte Verantwortungen

Der read-only Generator verantwortet ausschließlich die deterministischen
Manifestbytes.

Der spätere Handoff-Writer verantwortet ausschließlich die private, atomare
Ablage exakt dieser Bytes.

Der Owner verantwortet Zielauswahl, Retention, Review und jede spätere
Gitentscheidung.

Keine dieser Verantwortungen impliziert eine andere.

## Owner

Der aufrufende lokale Betriebssystemnutzer ist Owner des Handoffs.

Der Writer darf keinen fremden Benutzer, keine Workspace-Rolle und keine
caller-supplied Authority als Ersatz akzeptieren.

LQ-425 führt keine neue persistente Benutzer-, Workspace- oder Rollenabbildung
ein.

Die Ownergrenze ist lokal und gilt nur für das private Manifestartefakt.

## Zielwurzel

Der Owner muss eine explizite private Zielwurzel außerhalb des
Repository-Sourcebaums auswählen.

Die Zielwurzel muss:

- bereits existieren;
- ein echtes Verzeichnis sein;
- dem aktuellen Betriebssystemnutzer gehören;
- Modus `0700` besitzen;
- in jeder Pfadkomponente frei von Symlinks sein.

Der Writer darf die Zielwurzel nicht automatisch erstellen oder ihre
Berechtigungen reparieren.

## Zielname

Der Owner liefert einen neuen, begrenzten Handoffnamen.

Der Name darf nur ASCII-Buchstaben, Ziffern, Punkt, Unterstrich und Bindestrich
enthalten.

Er darf weder leer noch `.` oder `..` sein und keine Pfadtrennzeichen tragen.

Der finale Dateiname endet fest auf `.json`.

Ein vorhandener Name wird niemals überschrieben, fortgesetzt oder ersetzt.

## Nichtwiederverwendung

Ein finaler Zielname gehört genau einem erfolgreichen oder in seinem Ausgang
unklaren Handoffversuch.

Nach sichtbarem Erfolg darf derselbe Name nicht erneut verwendet werden.

Nach Timeout, Signal oder unbekanntem Ausgang darf derselbe Name erst nach
read-only Reconciliation bewertet werden.

Fehlt das Ziel nach beweisbarer Reconciliation, ist damit noch keine globale
Namens-Nichtwiederverwendung belegt.

Eine dauerhafte Attempt-Registry bleibt ein separater späterer Slice.

## Manifestquelle

Der Writer muss die Manifestbytes im selben kontrollierten Aufruf direkt vom
gehärteten read-only Generator erhalten.

Er akzeptiert keine caller-supplied JSON-Datei, keinen Allow-Boolean und keine
frei angegebene Dateizahl oder Digestentscheidung.

Die Bytes müssen kanonisches Schema 1 sein und alle vier Autorisierungsfelder
auf `false` setzen.

Der Writer verändert, formatiert oder erweitert die Bytes nicht.

## Commit- und Scopebindung

Der Manifestinhalt bindet:

- den vollständigen Base-Commit;
- detached oder benannten Branchzustand;
- die exakte dateigenaue Inventur;
- Modus, Größe und SHA-256 jeder Datei;
- Reviewabdeckung;
- die expliziten Nichtautorisierungen.

Der Writer darf keinen dieser Werte aus separaten CLI-Argumenten ersetzen.

## Private temporäre Datei

Der Writer erzeugt eine neue temporäre Datei im selben Zielverzeichnis wie
die finale Datei.

Die temporäre Datei muss:

- exklusiv neu erzeugt werden;
- ein nicht vorhersagbares, nicht wiederverwendetes Suffix tragen;
- Modus `0600` besitzen;
- eine reguläre Datei ohne Symlink sein;
- exakt die kanonischen Manifestbytes enthalten.

Same-Directory ist erforderlich, damit der finale Verzeichniswechsel nicht
über Dateisystemgrenzen führt.

## Atomare Erzeugung

Die kontrollierte Reihenfolge lautet:

1. Zielwurzel und Eigentum frisch prüfen;
2. finales Ziel auf Abwesenheit prüfen;
3. Manifest direkt read-only erzeugen;
4. temporäre Datei exklusiv mit `0600` anlegen;
5. alle Bytes vollständig schreiben;
6. Datei flushen und `fsync` ausführen;
7. Dateityp, Modus, Größe und SHA-256 aus dem offenen Descriptor prüfen;
8. finales Ziel erneut auf Abwesenheit prüfen;
9. ohne Overwrite atomar an den finalen Namen binden;
10. Zielverzeichnis `fsync`en;
11. finale Datei read-only erneut prüfen;
12. erst danach Erfolg ausgeben.

Ein normales Replace mit Overwrite-Semantik ist nicht zulässig.

## Sichtbare Erfolgsantwort

Erfolg darf nur eine begrenzte Aussage enthalten:

- `outcome=manifest_handed_off`;
- finalen Dateinamen ohne absoluten Pfad;
- SHA-256 der kanonischen Manifestbytes;
- Dateizahl;
- `staging_authorized=false`;
- `commit_authorized=false`.

Der absolute Zielpfad, Ownername und interne temporäre Name werden nicht
ausgegeben.

## Neutraler Ausgang

Ein bereits vorhandenes finales Ziel ist kein Erfolg und keine technische
Unverfügbarkeit.

Es ist eine neutrale Nichtausführung mit `target_not_absent`.

Der Writer liest, verändert oder vergleicht den vorhandenen Inhalt in diesem
Pfad nicht.

Auch ein inzwischen veränderter Sourcezustand vor temporärer Erzeugung endet
neutral ohne Datei als `source_not_stable`.

Diese neutralen Ausgänge autorisieren keinen Retry mit demselben Namen.

## Detailfreie technische Unverfügbarkeit

Nicht eindeutig klassifizierbare Fehler bei Eigentum, Pfadprüfung,
Manifestmessung, Open, Write, Flush, `fsync`, Link, Verzeichnis-Sync oder
finaler Verifikation enden detailfrei als `manifest_handoff_unavailable`.

Interne Pfade, Betriebssystemfehler, Dateiinhalt und Ownerdetails werden nicht
ausgegeben.

LQ-425 benennt keinen neuen domänenweiten Exceptiontyp.

## Unbekannter Ausgang

Nach möglichem finalem Bindeeffekt, aber vor bestätigter Verzeichnis-
Durability oder finaler Verifikation, ist der Ausgang unbekannt.

Der Writer darf dann:

- keinen Erfolg behaupten;
- den finalen Namen nicht erneut verwenden;
- keinen zweiten Write oder Bind versuchen;
- die finale Datei nicht löschen;
- nur an read-only Reconciliation übergeben.

## Read-only Reconciliation

Die spätere Reconciliation darf ausschließlich prüfen:

- ob der exakte finale Name vorhanden ist;
- ob er regulär, nicht symbolisch, owner-kontrolliert und `0600` ist;
- ob seine Bytes kanonisches Manifest-Schema 1 bilden;
- ob Digest und Dateizahl aus den Bytes selbst ableitbar sind;
- ob alle vier Autorisierungsflags weiterhin `false` sind.

Sie darf keine Source-Datei, Manifestdatei oder Gitgrenze verändern.

## Retention

Vor finaler Bindung ist die untere Retentionsgrenze der temporären Datei nur
die Dauer des aktiven Handoffversuchs.

Bei eindeutigem Fehler vor möglichem Bindeeffekt muss sie entfernt werden.

Nach unbekanntem Ausgang darf eine möglicherweise relevante temporäre Datei
nicht blind gelöscht werden; sie wird an Incident-Reconciliation übergeben.

Nach Erfolg bleibt die finale Datei mindestens bis zum Abschluss von Review,
Stagingentscheidung und gegebenenfalls Commitverifikation erhalten.

Eine spätere Löschung benötigt eine separate owner-kontrollierte
Retentionentscheidung.

## Git- und Releasegrenze

Das persistierte Manifest ist keine Stagingliste und kein Gitbefehl.

Es autorisiert insbesondere nicht:

- `git add`;
- Brancherzeugung;
- Commit oder Push;
- Pull Request;
- Build oder PostgreSQL-Lauf;
- Signatur, Promotion, Publication oder Deployment.

Diese Aktionen bleiben separat freizugeben.

## Audit und Logging

Der Writer darf keine Manifestbytes oder Dateipfade in allgemeine Logs
schreiben.

Zulässig sind nur begrenzte Outcome-, Digest- und Zählungswerte ohne
Source- oder Zielpfad.

LQ-425 führt keinen neuen persistenten Auditstore ein.

## Nichtziele

LQ-425 implementiert keinen Writer, Reconciler, CLI, Port, Modell, Migration
oder Entry Point.

Der Slice entscheidet keine konkrete Attempt-ID-Persistenz und keine
automatische Retentionmutation.

Er erzeugt keine Datei und verändert weder Gitindex noch Historie.

Er installiert keine Dependency, baut kein Artefakt und greift auf kein
externes System zu.

## Nächster Slice

LQ-426 sollte den owner-kontrollierten privaten Manifest-Writer exakt nach
diesem Vertrag implementieren.

Er bleibt eine explizite lokale Moduloberfläche ohne installierten Entry Point,
automatisches CI-Wiring, Staging- oder Commitauthority.
