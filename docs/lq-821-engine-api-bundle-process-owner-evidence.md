# LQ-821 — Engine API Bundle Process Owner Evidence

## Entrypointevidenz

Tests belegen genau einen Settingsload, genau eine Bundlecomposition und genau
einen Run auf derselben Bundleinstanz.

## Claimevidenz

Zwei konkurrierende Caller ergeben genau einen laufenden Gewinner und eine
sofortige Ablehnung. Nach Runfehler bleibt der Claim verbraucht und private
Fehlerdetails verlassen die Grenze nicht.

## Healthevidenz

Während der Gewinner im Run blockiert, liefern Readiness und Snapshot ohne
Warten den aktuellen `serving`-Zustand.

## Oberflächenevidenz

Fremde Bundles werden abgelehnt. Der Owner besitzt keine Start-, Join-, Close-
oder Serveroberfläche und erzeugt selbst keinen Thread.
