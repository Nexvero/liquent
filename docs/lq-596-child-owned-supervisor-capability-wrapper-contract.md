# LQ-596 — Child-owned Supervisor Capability Wrapper Contract

## Ergebnis

LQ-596 definiert den einzigen zulässigen Wrapperablauf im gebundenen Writer-
oder Recoverycontainer.

Der Slice implementiert noch keinen Containerentrypoint.

## Feste Profile

Es existieren genau zwei konstruktiv getrennte Wrapperprofile: Writer und
read-only Recovery.

Kein Request wählt Executable, Modul, Command, Args oder Environment.

Das Image-Digest und das LQ-591-Entrypointprofil legen den Code fest.

## Gebundener Input

Der Wrapper erhält ausschließlich das private Control-Mountprofil und die beim
Containercreate fest gebundenen internen Korrelationen.

Er liest keine Session, Rolle, Permission oder caller-supplied Authority.

Source, Target und Handoffname müssen aus einem kanonischen, digestgebundenen
Jobdokument stammen; freie Environmentwerte sind kein Ersatz.

## Start ohne Capabilitywirkung

Nach Prozessstart öffnet der Wrapper weder Source noch Target.

Er validiert zuerst Control-Directory, Binding und erwartete Artefaktrollen.

Vor erfolgreichem Ready darf kein Writer- oder Recoverymodul importiert oder
aufgerufen werden.

## Direktes Ready

Nur der Kindprozess publiziert sein Ready-Artefakt.

Ready bindet Handle, Gatebinding, Profil und die unveränderliche
Wrapperinstanz.

Der Parent liest und persistiert den Nachweis, publiziert ihn aber nicht.

Ein vorhandenes fremdes oder divergentes Ready endet fail-closed.

## Einmaliger Releasekonsum

Der Wrapper wartet begrenzt auf genau das gebundene Release-Token.

Nur exakt passende Release-ID, Handle und Profil werden akzeptiert.

Der Wrapper publiziert selbst genau ein Consumed-Artefakt, bevor er
Capabilitycode lädt.

Wiederholung, Divergenz oder Mehrdeutigkeit erzeugt keine zweite Wirkung.

## Writerwirkung

Das Writerprofil ruft genau die bestehende kontrollierte Manifestwritergrenze
mit dem gebundenen Source-, Target- und Handoffnamen auf.

Es gibt keinen Retry nach möglicher Dateiwirkung.

Geschlossene Writerausgänge werden unverändert in ein begrenztes
Terminaldokument übersetzt.

## Recoverywirkung

Das Recoveryprofil ruft ausschließlich den bestehenden read-only Reconciler
auf.

Es erhält keine Writer-, Cleanup-, Registry- oder Authorityfähigkeit.

Die geschlossene Recoverymatrix bleibt vollständig erhalten.

## Terminal-Envelope

Nach direktem Capabilityende publiziert ausschließlich der Wrapper genau ein
kanonisches Terminal-Envelope.

Envelope bindet Handle, Profil, Release und geschlossenen Outcome.

Freies stdout, stderr, Exitcode oder Exceptiontext ist kein Outcome.

Kann kein sicherer Ausgang bestimmt werden, wird ausschließlich der bestehende
geschlossene Unknown-/Unavailable-Ausgang verwendet.

## Prozessende

Erst nach dauerhaftem Terminal-Envelope darf der Wrapper normal enden.

Ein Ende ohne valides Envelope bleibt für den Parent technische
Unverfügbarkeit und keine fachliche Terminalität.

PID-Abwesenheit allein erzeugt keinen Outcome.

## Minimales Environment

Locale und Encoding sind fest.

Ungeprüfte Hostvariablen, Datenbank-DSN, Plattformtokens und Controllersecrets
werden nicht vererbt.

Nicht benötigte Deskriptoren und Sockets bleiben geschlossen.

## Größen- und Zeitgrenzen

Alle Control-Dokumente besitzen feste Versions- und Bytegrenzen.

Gatewait und Terminalpublikation besitzen kontrollierte technische Grenzen,
aber Timeout erzeugt keine zweite Ausführung.

Output wird nicht unbegrenzt gepuffert.

## Crash und Retry

Ein Wrapperrestart ist kein automatischer Capabilityretry.

Vor jedem möglichen Wiederanlauf müssen Consumed-, Terminal- und
Enginezustand direkt korreliert werden.

Bei unklarem früherem Konsum bleibt der Job gesperrt.

## Fehlergrenze

Artefakt-, Decode-, Binding-, Capability- und Dateifehler verlassen den
Wrapper nur als geschlossener Outcome oder detailfreie technische
Unverfügbarkeit.

Interne Pfade, IDs und Exceptions werden nicht ausgegeben.

Es wird kein neuer öffentlicher Exceptiontyp benannt.

## Keine Implementation

LQ-596 ergänzt keinen Entrypoint, kein Image, keine Route, Migration,
Appfactory-, Compose- oder Deploymentwirkung.

## Nächster Slice

LQ-597 definiert die korrigierte Parent-Servicegrenze, die Wrapperfakten nur
beobachtet und nie stellvertretend publiziert oder doppelt ausführt.
