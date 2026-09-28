# LQ-461 — Closed Manifest Handoff Supervisor Engine Contract

## Ergebnis

LQ-461 definiert die geschlossene Enginegrenze für Create, Inspect, Start,
Wait und Terminate.

Der Slice implementiert keinen Dockerclient und spricht keine Engine an.

## Ein Port

`ManifestHandoffSupervisorEngine` besitzt genau fünf Methoden.

Die Methoden nehmen ausschließlich typisierte Requestobjekte an.

Ein Caller kann keine freie Operation oder Engineaktion benennen.

## Geschlossene Profile

Das Prozessprofil ist exakt Writer oder Recovery.

Writer und Recovery bleiben unterschiedliche Capabilityprofile.

Ein freier Entrypoint, Command, Args oder Environmentwert ist ausgeschlossen.

Das konkrete Profil wird konstruktiv durch den späteren Adapter aufgelöst.

## Create

Create bindet Handle, Creation-ID, Control-Directory-ID, Image-Digest und
geschlossenes Profil.

Der Request enthält keinen Containername, Hostpfad oder Imagenamen.

Der Imagewert ist weiterhin ausschließlich ein unveränderlicher sha256-Digest.

Ein erfolgreicher Record ergänzt nur die Engine-Container-ID.

## Create-Unknown

Ein Retry verwendet dieselbe nicht wiederverwendbare Creation-ID.

Der spätere Adapter muss nach dieser Identity inspizieren, bevor er erneut
erzeugt.

Exakt passender Bestand darf als derselbe Create-Ausgang zurückkehren.

Abweichender oder mehrdeutiger Bestand ist detailfreier Konflikt.

Neutrales `None` ist nur zulässig, wenn autoritativ keine Create-Wirkung
vorliegt.

## Kein Callerprofil

Mounts, Netzwerk, User, Linux-Capabilities und Ressourcenlimits sind nicht im
Request enthalten.

Restartpolicy `no`, kein Auto-Remove, read-only Rootfilesystem und feste
Mountprofile bleiben Adapterkonfiguration.

Ein Request kann diese Sicherheitswerte weder lockern noch ersetzen.

## Inspect

Inspect adressiert ausschließlich die unveränderliche Runtime-Container-ID.

Die Beobachtung bindet Container-ID, Creation-ID, Image-Digest, Profil und
geschlossenen Enginezustand.

Name, Label oder PID sind kein Ersatzhandle.

Ein erwarteter fehlender gebundener Container ist nicht neutral.

## Enginezustände

Der Vertrag kennt ausschließlich created, running, exited und dead.

Andere, beschädigte oder nicht belegte Enginezustände scheitern fail-closed.

Exited und dead sind direkte Runtime-Terminalbeobachtungen.

Created oder running sind niemals Terminalnachweise.

## Kein fachliches Outcome

Die Enginebeobachtung enthält kein Manifest- oder Recoveryergebnis.

Sie enthält bewusst keinen Exitcode.

Terminale Runtime plus valides separates Envelope werden später korreliert.

Enginezustand allein erzeugt keinen fachlichen Erfolg.

## Start

Start adressiert nur die persistiert gebundene Runtime-Container-ID.

Annahme liefert eine typisierte Bestätigung derselben ID.

Sie behauptet weder Ready noch Running noch Capabilityausführung.

Vor Start muss die Composition die persistente Binding vollständig prüfen.

## Kein blinder Neustart

Ein bereits gestarteter oder terminaler Container darf nicht erneut gestartet
werden.

Nach Daemon- oder Serviceneustart ist zuerst direkt zu inspizieren.

Der Port bietet keine Restartoperation.

Ein zweiter Startversuch wird nicht als idempotenter Erfolg erfunden.

## Wait

Wait beobachtet dieselbe Runtime-Container-ID bis zu einer konstruktiv
begrenzten Adapterpolicy.

Der Request akzeptiert keinen Timeout und keine Pollingparameter.

Nur exited oder dead dürfen als erfolgreicher Wait-Ausgang zurückkehren.

Eine noch laufende Runtime oder abgelaufene technische Wartefrist bleibt
detailfreie technische Unverfügbarkeit, nicht Terminalität.

## Terminate

Terminate bindet Runtime-Container-ID und persistente Terminate-ID.

Die Methode darf erst nach durablem Terminate-Journalfakt aufgerufen werden.

Ihre Bestätigung bedeutet ausschließlich, dass die Engineanforderung für
diese Korrelation angenommen wurde.

Stop- oder Kill-Annahme ist kein Terminalnachweis.

Danach bleibt Wait beziehungsweise Inspect bis exited oder dead erforderlich.

## Kein Remove

Der Port besitzt keine Remove-, Prune- oder Cleanupoperation.

Container und Enginebeobachtung bleiben bis zur späteren Retentionentscheidung
erhalten.

Ein terminaler Container darf in diesem Slice nicht gelöscht werden.

## Ergebnisse

Create, Start und Terminate besitzen getrennte Bestätigungstypen.

Inspect und Wait teilen die direkte geschlossene Enginebeobachtung.

Es gibt keinen caller-gelieferten oder zurückgegebenen Allowboolean.

IDs und Requests sind repr-frei, soweit sie interne Werte tragen.

## Neutrale Abwesenheit

`None` bedeutet ausschließlich eine neutral belegte Abwesenheit oder
Nichtannahme an der jeweiligen Grenze.

Es beweist keine Terminalität, keine Authority und keinen fachlichen Ausgang.

Ein erwarteter fehlender Container, unbekannter Zustand oder unklare
Create-Wirkung ist nicht neutral.

## Konflikt

`ManifestHandoffSupervisorEngineConflict` ist feldlos und detailfrei.

Er vereinheitlicht divergente Creation-, Image-, Profil- oder
Runtimezuordnungen und fremden Bestand.

Der Konflikt enthält keine Engine- oder Hostdetails.

## Technische Unverfügbarkeit

Daemon-, Socket-, Protokoll-, Timeout- und Decodefehler bleiben an der
bestehenden detailfreien technischen Grenze.

LQ-461 benennt keinen neuen Exceptiontyp.

Technische Unverfügbarkeit darf nicht in `None`, Konflikt oder Terminalität
umgedeutet werden.

## Keine Authority

Der Vertrag akzeptiert keine Session, User-ID, Rolle, Permission oder
Allowentscheidung.

Ein Containerhandle oder Enginezustand erteilt keine Writer- oder
Recoveryfähigkeit.

Aktuelle Authority und Journalvoraussetzungen bleiben Sache der Composition.

## Kein Infrastrukturinput

Socket, Host, Context, TLS, Pfad, PID und Enginecredentials sind keine
Requestfelder.

Nur der spätere minimal privilegierte Supervisoradapter besitzt den lokal
konfigurierten Enginezugang.

Remote Engine und Popen-Fallback bleiben ausgeschlossen.

## Keine Persistenz- oder Dateiwirkung

LQ-461 ändert kein Schema und schreibt keine Runtimebinding.

Der Port liest oder veröffentlicht kein Control-Artefakt.

Control-Directory-ID ist eine Korrelation und kein offengelegter Hostpfad.

## Migration und Wiring

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, Docker-SDK-Adapter, CLI-, Compose-, Route-, CI-
oder Production-Wiring.

## Tests

Fokussierte Tests belegen zwei Profile, vier Zustände, geschlossene Requests,
getrennte Bestätigungen, fünf Portmethoden und fehlende freie Prozessparameter.

## Nächster Slice

LQ-462 sollte den Docker-Engine-Adapter gegen diesen Vertrag implementieren.

Der atomare Control-Artefaktcodec und Filepublisher bleiben danach separat.
