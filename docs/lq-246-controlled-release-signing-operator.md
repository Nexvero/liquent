# LQ-246 — Controlled Release Signing Operator

## Ergebnis

LQ-246 ergänzt den owner-only Offline-Operator für LQ-245 und materialisiert
eine persistierte Signing-Entscheidung als detached SSHSIG und kanonische
Decision-Evidence.

Der Operator promotet, veröffentlicht und deployt den Kandidaten nicht.

## Prozessgrenze

Der neue Entry Point lautet `liquent-release-signing`.

Er ist ein explizit gestarteter Offline-Command und keine HTTP-Route, kein
Startup-Hook, kein Deployment-Schritt und kein automatischer CI-Effekt.

Die Liquent-App verdrahtet ihn nicht automatisch. Datenbank, Executor-ID,
Request und privater Key werden über explizite lokale Operatorpfade gebunden.

## Private Eingaben

Datenbank-URL, Executor-ID, Request und privater Key müssen reguläre,
nicht verlinkte Dateien ohne Group-/Other-Rechte sein.

Der geschlossene Request enthält exakt:

- Signing-Decision-ID;
- Key-ID;
- erwartete Registry-Revision;
- Bundle-Pfad;
- Signatur-Zielpfad;
- Evidence-Zielpfad.

Authority-ID, Public Key, Fingerprint, Policy, Status, Rolle, Algorithmus,
Namespace, Allow-Wert und Promotionentscheidung sind keine Requestfelder.
Unbekannte Felder werden abgelehnt.

Der Signaturdateiname muss exakt `<bundle-name>.sshsig` sein. Signatur und
Evidence dürfen nicht denselben Zielpfad bezeichnen.

## OpenSSH-Key-Provider

Der kontrollierte Provider verwendet den expliziten privaten Key nur über das
lokale `ssh-keygen`.

Vor Signierung berechnet er dessen SHA-256-Fingerprint. LQ-245 vergleicht
diesen mit dem aktuellen persistenten Registry-Fakt, bevor der Provider die
Payload erhält.

Signiert werden ausschließlich die von LQ-245 aus demselben Bundle-Snapshot
extrahierten `SHA256SUMS`-Bytes unter Namespace
`liquent-operations-release-v1`.

Private Keybytes werden weder durch den Operator gelesen und weitergereicht
noch in Datenbank, Resultat, Evidence, stdout oder stderr ausgegeben.

## Unabhängige Verifikation

Ein getrennter OpenSSH-Adapter erzeugt aus dem von der Registry aufgelösten
Public Key und der Signer-Authority eine temporäre `allowed_signers`-Grenze.

Er verifiziert die erzeugte SSHSIG erneut über die exakten Checksumbytes und
den festen Namespace. Erst ein erfolgreicher Verify erlaubt LQ-245 den
persistenten Commit.

Temporäre Payload-, Signatur- und Allowed-Signer-Dateien leben nur in privaten
temporären Verzeichnissen und werden nach dem Aufruf entfernt.

## Persistenz vor Ausgabe

Die LQ-245-Entscheidung wird vor finaler Dateimaterialisierung committet.

Schlägt die Ausgabe danach fehl, bleibt die persistierte Entscheidung der
maßgebliche Wiederaufnahmepunkt. Ein Retry derselben Decision-ID liest
dieselben Signatur- und Evidence-Bytes ohne erneute Signierung.

Ein Dateisystemerfolg ohne persistierte Signing-Entscheidung ist dadurch
ausgeschlossen.

## Exklusive Ausgabe

Beide Zielverzeichnisse müssen bereits existieren und dürfen keine Group- oder
Other-Rechte besitzen.

Signatur und Evidence werden zunächst unter eindeutig besessenen temporären
Namen mit `O_EXCL`, Modus `0600`, vollständigen Writes und `fsync` erzeugt.

Die finalen Namen entstehen über exklusive Hardlinks. Bereits vorhandene
Ziele werden nie geöffnet, gekürzt, ersetzt oder überschrieben.

Nach erfolgreicher Verlinkung werden die betroffenen Verzeichnisse
synchronisiert und die temporären Namen entfernt.

## Fehlerbereinigung

Wenn ein im Prozess sichtbarer Fehler zwischen beiden finalen Links auftritt,
entfernt der Operator ausschließlich die von diesem Versuch erzeugten Links
in umgekehrter Reihenfolge.

Fremde oder bereits vorhandene Dateien werden niemals entfernt. Temporäre
Dateien werden auch im Fehlerpfad bestmöglich bereinigt.

Ein Prozessabbruch außerhalb kontrollierter Fehlerbehandlung kann weiterhin
einen einzelnen finalen Link hinterlassen. Dieser partielle Zustand wird beim
nächsten Start fail-closed erkannt und niemals automatisch als Erfolg oder
Eigentumsnachweis interpretiert.

## Exakter Retry

Existieren beide Zieldateien bereits als private reguläre Dateien und stimmen
ihre Bytes exakt mit der persistierten Entscheidung überein, liefert der
Operator `recovered`.

Existiert nur ein Ziel, ist ein Ziel ein Symlink, besitzt es zu weite Rechte
oder weichen Bytes ab, endet der Retry detailarm technisch nicht verfügbar.

Der Operator überschreibt oder repariert solche ambivalenten Ziele nicht.
Eine kontrollierte owner-only Incidententscheidung muss sie zunächst prüfen.

## Ergebnis und Exit-Semantik

stdout enthält ausschließlich detailarmes kanonisches JSON:

- `signed` für neue vollständig materialisierte Ausgaben;
- `recovered` für ein bytegleiches vollständiges Retry-Paar;
- `rejected` bei fehlender aktueller Signing-Authority.

Inputfehler, Decision-ID-Konflikt und technische Nichtverfügbarkeit besitzen
getrennte Exitcodes. stderr enthält nur den jeweiligen stabilen Fehlercode.

Keine Ausgabe nennt DSN, Pfade, private Keys, Providerdetails, SQL,
Registry-Inventare oder ursprüngliche Exceptions.

## Bundle-Inventar

Der neue Operator ist ein installierter Console Entry Point und Teil des
Runtime-Wheels. Das LQ-236-Inventargate erwartet deshalb nun dreizehn Entry
Points und elf Operatormodule einschließlich Package-Initialisierung.

Bundle-Format, Migrationenzahl und Migration-Head bleiben unverändert.
LQ-246 benötigt keine Schemaänderung oder Migration.

## Nachweis

Tests belegen:

- geschlossenes privates Requestformat;
- Ablehnung caller-gelieferter Allow-Fakten;
- exklusive private Ausgabe ohne Überschreiben;
- bytegleichen vollständigen Retry;
- fail-closed partielle und abweichende Ziele;
- Ablehnung unsicherer Zielverzeichnisse;
- echte Ed25519-SSHSIG-Erzeugung und unabhängige OpenSSH-Verifikation;
- aktualisierte Wheel-, Entry-Point- und Operatorinventare.

Die vollständige Pflichtsuite besteht mit echtem PostgreSQL 16:

```text
3034 passed, 56 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-246 enthält keine Registry- oder Key-Mutation, Key-Erzeugung, Rotation,
Revocation, Promotion, Veröffentlichung, Package-Versionierung, Git-Aktion,
Deployment- oder Production-Wiring-Änderung.

Der Operator verwaltet keinen HSM-, Agent- oder Cloud-KMS-Provider und gibt
keine Aussage über langfristige private Key-Retention.

## Nächster Slice

LQ-247 sollte den kontrollierten Release-Promotion-Operator entscheiden und
implementieren. Er muss LQ-244 direkt gegen die persistente Projektion nutzen,
Signatur und Bundle read-only prüfen, detailarme Promotion-Evidence exklusiv
materialisieren und weiterhin weder veröffentlichen noch deployen.
