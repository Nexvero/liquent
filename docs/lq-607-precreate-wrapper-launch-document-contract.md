# LQ-607 — Pre-create Wrapper Launch Document Contract

## Ergebnis

LQ-607 konkretisiert den LQ-604-Vertrag als additive, vollständig vor Docker
Create konstruierbare Startbindung.

## Inhalt

Das Dokument bindet Document-ID, Creation-ID, Handle, Control-Directory,
Profil und Image-Digest.

Es bindet Ready-, Consumed- und Terminal-Artefakt-ID sowie Gated- und
Terminal-Observation-ID.

Claim, Owner, Scope-ID, Source, Target und Handoffname sind eingeschlossen.

## Kein Runtimezirkel

Die Runtime-Container-ID ist ausdrücklich kein Dokumentfeld.

Sie entsteht erst nach Create und bleibt getrennte Parent-/Engine-/
Persistenzkorrelation.

Der vollständige Launchdocumentdigest kann damit vor Create feststehen.

## Profile

Writer verlangt Execution-Claim und Execution-Owner.

Recovery verlangt Recovery-Claim und Recovery-Owner.

Cross-Profile, Cleanup und freie Capabilitywerte sind ungültig.

## Kanonische Integrität

Schema und Version sind fest.

Exakte Keys, eindeutige JSON-Felder und Byte-Roundtrip sind verpflichtend.

SHA-256 und Byteanzahl binden den vollständigen kanonischen Inhalt.

## Keine Authority

Das Dokument enthält keine Session, Rolle, Permission, Allowentscheidung oder
Credentials.

Claim und Owner sind enge Jobbindungen und keine allgemeine Authority.

## Keine Aktivierung

LQ-607 ergänzt noch keine Engine-Labels, Dateiübergabe, Mounts, UID/GID,
Wrapper- oder Parentservicewirkung.

## Nächster Slice

LQ-608 implementiert geschlossene Typen und den kanonischen Codec.
