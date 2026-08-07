# LQ-172 — OIDC Callback Completion und Session-Handover

## 1. Status, Ziel und Systemgrenze

Architekturentscheidung, **nur Vertrag**. Kein Modell, kein Port, keine
Fehlerklasse, kein Anwendungsfall, keine Route, kein Wiring, kein Test.

Aus einem bereits erfolgreich erzeugten `VerifiedOidcCallback` (LQ-163) wird
**genau ein** interner `UserId` bestimmt und anschließend **genau eine** frische
Browser-Session mit neuem CSRF-Material erzeugt. Mehr nicht. Der Vertrag baut
auf LQ-129/131/132/133 und LQ-114/115/119 sowie LQ-155/158/163/171 und liefert
die interne Completion-Grenze, die **LQ-158 §14** abgewartet hat.

## 2. Eingangsgrenze

Die Completion sieht **keinen** Authorization Code, **kein** ID-Token, **kein**
State und **kein** Binding-Cookie, und prüft Issuer, Signatur und Claims **nicht
erneut** — das ist vor ihr abgeschlossen (LQ-171). Sie nimmt **keinen** frei
gewählten `UserId` und **keine** Workspace-, Rollen- oder Berechtigungswerte aus
dem Browserrequest und erzeugt **niemals** automatisch einen User. `identity`,
`admission_id` und `return_path` stammen ausschließlich aus dem bereits
geclaimten serverseitigen Login-Record.

## 3. Identitätsauflösung

1. `ExternalIdentityLookup.get_user_id(identity)` **genau einmal**.
2. Liefert er einen `UserId`: **exakt diesen** verwenden.
3. Kein `UserId` und `admission_id is None`: neutrale fachliche Ablehnung.
4. Kein `UserId` und Admission vorhanden:
   `consume_admission_and_bind(admission_id, identity)` **genau einmal**;
   zulässig ist **ausschließlich** der aus der Admission stammende `UserId`,
   `None` ist neutrale fachliche Ablehnung.
5. **Kein** zweiter Lookup, **kein** zweiter Admission-Versuch, **kein**
   Fallback, **kein** frei gewählter User.

### Bestehendes Binding hat absoluten Vorrang

Liefert der Lookup einen `UserId`, wird eine vorhandene Admission **weder
geprüft noch konsumiert**, kein schreibender Binding-Port aufgerufen, keine
Übereinstimmung mit dem Admission-Ziel vorausgesetzt oder hergestellt, und es
gibt kein Rebinding und keinen Account-Merge.

Die Bindung `(issuer, subject) → UserId` ist nach LQ-132 eindeutig und wird nie
umgebogen. Die Admission ist eine **einmalig konsumierbare Capability für die
erstmalige Bindung**: Verbrauchte sie ein bloßer Zweitlogin, ginge ein
Onboarding-Recht ohne sichtbare Wirkung verloren, und es entstünde eine zweite,
konkurrierende Quelle für den `UserId`. Der Vorrang macht diese Wahl unmöglich.

## 4. Race nach negativem Lookup

Das anfängliche Lookup darf negativ sein, während ein paralleler Vorgang
anschließend bindet. Ein **zweiter Lookup wird nicht verlangt**. Es entscheidet
allein der atomare `consume_admission_and_bind`-Aufruf:

- eine identische, idempotente Bindung darf den zugehörigen `UserId` liefern;
- eine Kollision oder anderweitige Bindung bleibt neutral `None`;
- **kein** Fallback auf einen danach erneut gelesenen User;
- **kein** Check-then-act im Completion-Anwendungsfall.

Die Admission-Grenze bleibt die **einzige atomare Schreibentscheidung**: keine
eigene Persistenzlogik, kein Rebinding, kein Überschreiben und keine
Mitgliedschaft, Rolle oder Workspace-Berechtigung (LQ-129).

## 5. Session-Erzeugung

Erst nachdem **genau ein** `UserId` belastbar feststeht, wird daraus ein
`SessionPrincipal` gebildet und **genau einmal** die bestehende
Session-Issuance-Grenze verwendet: neue kryptografisch erzeugte Session-ID,
neues **unabhängiges** CSRF-Material, feste serverseitige Lebensdauer, atomar
gespeicherter Record, Handover ausschließlich als `IssuedBrowserSession`.
**Keine** Session-ID und **keine** CSRF-Werte aus Callback, Query, Cookie,
Providerdaten, Claims, Admission oder `return_path`.

Die Zeit stammt ausschließlich serverseitig, die Lebensdauer aus der bestehenden
Issuance-Grenze — **keine** Zeit aus Request, Provider, Token, Claim oder
Browser. Clock und Generator werden **erst nach** belastbarer Ermittlung des
`UserId` berührt; bei fachlicher Ablehnung entstehen **weder** ein Clock-Read
**noch** Session- oder CSRF-Material. Die bestehenden Session-Zeitverträge
werden weder neu definiert noch dupliziert.

## 6. Bestehende Browser-Session

Eine eventuell vorhandene Anwendungssession ist **keine Autoritätsquelle**.
Die Completion erzeugt eine **frische** Session; sie übernimmt und verlängert
keine vorhandene Session-ID und rotiert **nicht** über eine unvalidierte ambient
Session-Cookie-ID — eine solche ID gelangt gar nicht erst in ihre Signatur. Sie
widerruft **keine** vorhandene Session als Nebenwirkung eines GET-Callbacks; der
neue Cookie-Slot darf später im Browser überschrieben werden, ein serverseitiger
Widerruf anderer Sessions ist eine getrennte Account- und
Session-Management-Entscheidung.

Damit existiert **kein** Session-Fixation-Pfad über eine vom Browser gelieferte
alte Session-ID. Globale Abmeldung, Rotation und Widerruf anderer Sessions
entscheidet LQ-172 nicht.

## 7. CSRF-Handover

Der Callback selbst verlangt **kein** Anwendungs-CSRF-Token: Browserbindung und
atomarer Einmal-Claim (LQ-158) sind die vorgelagerten Schutzgrenzen. Nach
erfolgreicher Completion entsteht neues CSRF-Material zusammen mit der
neuen Session, bleibt serverseitig an **genau diese** Session gebunden und
erreicht den späteren Transport **ausschließlich** über den bestehenden
Session-Issuance-Response-Helfer. Es erscheint nie in URL, Redirect-Ziel, Body,
Log, Telemetrie oder Metriklabel. Bei fachlicher Ablehnung oder technischer
Unverfügbarkeit entsteht **weder** Session **noch** CSRF-Material.

## 8. Ergebnisgrenze

Die spätere transportfreie Ausgabe enthält **ausschließlich** die neue
`IssuedBrowserSession` und den optionalen serverseitigen `return_path`, beide
vollständig vor `repr` geschützt. **Keine** `ExternalIdentity`, **kein**
`UserId`, **keine** Admission-ID, **keine** Claims und **keine** Providerdaten.
Konkrete Signatur und Klassenname bleiben dem Implementierungsslice vorbehalten.

## 9. Return-Path-Grenze

`return_path` wird hier **weder interpretiert noch als Redirect verwendet**:
kein Browserwert, keine Normalisierung, kein URL-Join, keine Host-, Scheme- oder
Forwarded-Header-Ableitung und keine Ausgabe vor einer eigenen
Validated-Internal-Destination-Grenze. Seine Aufnahme in die interne Ausgabe ist
ein **verlustfreies Handover** an diese spätere Grenze — er bleibt unvalidiert
und nicht transportfähig und ist **keine** Redirect-Freigabe. `None` bedeutet
später das feste sichere Standardziel; ein vorhandener String darf erst nach
erfolgreicher separater Validierung Ziel werden. Konkrete Zielpfade,
Statuscodes und Fehlerseiten nimmt LQ-172 nicht vorweg.

## 10. Fehlerklassen

Fachliche Ablehnung bleibt intern ein einheitliches `None`: ungebundene
Identität ohne Admission; Admission unbekannt, abgelaufen, konsumiert oder
kollidierend; Bindung nicht erfolgreich. Technische Nichtverfügbarkeit bleibt
davon getrennt: Lookup-Infrastruktur-,
Admission-Store-, Generator-, Clock- und Session-Store-Fehler sowie ein
Session-ID-Konflikt. Ein `SessionLifecycleConflict` **nach** belastbarer
Identitätsauflösung ist technische Nichtverfügbarkeit, **keine** fachliche
Ablehnung und **kein** Anlass für einen zweiten Generator- oder Store-Versuch im
selben Callback.

Dafür braucht die Completion eine **eigene** detailfreie Fehlergrenze, die
technische Fehler **vollständig** neutralisiert: Weder ein ursprünglicher
Fehlertext noch eine interne Exceptionkette darf sie verlassen — auch dann
nicht, wenn ein innerer Baustein den Fehler bereits neutralisiert hat, dessen
Cause oder Context aber noch interne Details trägt. Kein Fehler legt Identität,
User, Admission, Session-ID, CSRF, Return-Path oder interne Ursache offen.

**`OidcVerificationUnavailable` bleibt ausschließlich der vorgelagerten
Verifikationsgrenze zugeordnet** und wird für Completion-Fehler nicht
wiederverwendet: Ein Transport kennt diesen Vertrag bereits, und zwei
verschiedene Ursachen dort zusammenzulegen machte sie ununterscheidbar. Der
endgültige Klassenname folgt im Implementierungsslice.

## 11. Teilfortschritt und kein Rollback

```
Callback bereits geclaimt
 → Identität auflösen  oder  Admission atomar konsumieren und binden
 → neue Session atomar speichern
 → später Transportantwort erzeugen
```

Die Reihenfolge ist irreversibel; die Login-Transaktion ist **vor** dieser
Grenze bereits konsumiert. Eine erfolgreiche Admission-Bindung bleibt bei einem
späteren Sessionfehler **wirksam** — ein Rollback würde einen verbrauchten
Capability-Handle wiederbeleben und Identitätszustände auseinanderziehen — und
eine gespeicherte Session wird **nicht** wegen eines Transportfehlers
zurückgerollt.

Fehler erzeugen **keinen** zweiten Claim, Code-Austausch, Verifikationsversuch,
Admission-Versuch oder Session-Issuance-Versuch. Ein neuer Versuch beginnt mit
einem **neuen Login-Start** und löst die nun gebundene Identität regulär über
den Lookup-Pfad auf. Orphaned-Session-Cleanup und globale Revoke-Politik sind
ein eigener Slice.

## 12. Bewusst noch nicht entschieden

Callback-Route, HTTP-Statuscodes, ob fachliche Ablehnung und technische
Nichtverfügbarkeit dasselbe Ziel verwenden, Redirect-Ziele, Cookie- und
CSRF-Header-Ausgabe im Handler, Löschung des OIDC-State-Cookies, Frontend-
Darstellung, das Validated-Internal-Destination-Modell sowie Wiring und
Persistenz. **LQ-158 bleibt dafür maßgeblich.** Der
Session-Issuance-Response-Helfer ist der später vorgeschriebene Ausgabekanal für
Cookie und CSRF-Header; LQ-172 ruft ihn nicht auf.

## 13. Nächster Schritt

Der Implementierungsslice mit Completion-Ausgabe, technischer Fehlergrenze und
transportfreiem Anwendungsfall.
