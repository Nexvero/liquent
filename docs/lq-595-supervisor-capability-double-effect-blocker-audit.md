# LQ-595 — Supervisor Capability Double-effect Blocker Audit

## Ergebnis

LQ-595 prüft, ob die in LQ-589 noch fehlenden Writer-/Recovery-
Capabilityprimitiven direkt hinter LQ-468 implementiert werden dürfen.

Die Entscheidung lautet: nein.

Der aktuelle Parent-/Kindprozessablauf enthält eine ungelöste Wirkungs- und
Ownershiplücke, die durch einen weiteren Supervisoradapter verdoppelt würde.

## Vorhandener Parent-Ablauf

LQ-475 erzeugt den Enginecontainer und startet ihn.

Danach publiziert der Parent über `FileManifestHandoffSupervisorGateWrapper`
selbst das Ready-Artefakt.

LQ-476 publiziert Release-Token und Consumed-Artefakt ebenfalls im Parent.

Anschließend beobachtet der Parent den Container als running und ruft den
LQ-468-Executor auf.

## Verdeckte zweite Wirkung

LQ-468 delegiert nach diesem Ablauf nochmals an
`ControlledManifestHandoffWriterSupervisor.release_writer` beziehungsweise
`release_recovery`.

Eine konkrete Implementation dieser Ports müsste eine weitere Capability
freigeben oder lokal ausführen.

Der bereits gestartete Container und diese zweite Primitive hätten keine
belegte gemeinsame physische Einmaligkeitsgrenze.

Damit könnte derselbe Claim zwei Writer- oder Recoverywirkungen erhalten.

## Ready ist nicht direkt

Der heutige Parent kann ein Ready-Artefakt publizieren, ohne dass der
Kindprozess direkt bestätigt hat, vor Capabilitycode am Gate zu warten.

Enginezustand running beweist weder Wrapperready noch einen ungeöffneten
Source-/Targetbestand.

Ein Parent-Artefakt ist kein direkter Kindprozesshandshake.

LQ-456 verlangt ausdrücklich einen gebundenen direkten Handshake vor Prepared.

## Consumed ist nicht direkt

Der Parent publiziert auch den Consumed-Nachweis.

Damit ist nicht belegt, dass genau der gebundene Wrapper genau dieselbe
Release-ID konsumiert hat.

Ein Parent kann keine Kindprozesswirkung durch eine eigene Dateiannahme
ersetzen.

LQ-456 verlangt die direkte Beobachtung des einmaligen Gatekonsums.

## Executorlage

`ExecuteManifestHandoffWriterCapability` und sein Recoverygegenstück binden
Gate, Prepared, Claim und Owner typseitig korrekt.

Der LQ-468-Adapter ist jedoch ein Kompatibilitätsadapter für die älteren
LQ-446-Supervisorports.

Er ist nicht die Kindprozessimplementation des Docker-Wrappers.

Seine direkte Productionverdrahtung würde die Layergrenzen vermischen.

## Outcome-Lücke

Der Parent erwartet von LQ-468 unmittelbar einen terminalen
`CompletedManifestHandoff*Process`.

Ein realer gestarteter Container kann nach Gatekonsum zunächst weiterlaufen.

Ein synchroner zweiter Supervisorabschluss ist daher kein Ersatz für direkte
Engine-Terminalität plus kindprozess-eigenes Terminal-Envelope.

## Kein Unknown-Stub

Ein Stub, der immer `outcome_unknown` liefert, würde einen Released-Job
terminalisieren, ohne die Capability ausgeführt oder direkt beobachtet zu
haben.

Ein No-op-Erfolg wäre noch schwerwiegender.

Beide Varianten bleiben verboten.

## Erforderliche Korrektur

Genau der gestartete Wrappercontainer muss Ready publizieren, Release
konsumieren, die fest eingebaute Capability einmal ausführen und sein
Terminal-Envelope publizieren.

Der Parent darf diese Kindprozessfakten nur lesen, validieren und persistent
korrelieren.

Er darf sie nicht stellvertretend erzeugen.

## Unveränderte Authority

Session, Rolle, Permission, Settings-Allow oder Enginebestand schließen diese
Lücke nicht.

Claim, Owner, Gate und Runtimebinding müssen aus dem System of Record stammen.

Revocation und Terminatebedingungen bleiben vor jeder Parentwirkung aktuell zu
prüfen.

## Productionentscheidung

Der neue LQ-591-Client ist als isolierte Enginekomponente verwendbar.

Der vollständige Productiongraph bleibt dennoch geschlossen.

Settings-, Lifespan-, Compose- und Socketmount-Aktivierung wären weiterhin
verfrüht.

## Keine Implementation

LQ-595 ändert keine Runtime-, Domain-, Port-, Settings-, Appfactory- oder
Composequelle.

Es ergänzt keine Migration, Tabelle oder SQL-Signatur.

Head bleibt `20260826_0042`.

## Nächster Slice

LQ-596 definiert den kindprozess-eigenen festen Capability-Wrappervertrag mit
direktem Ready, einmaligem Releasekonsum und terminalem Envelope.
