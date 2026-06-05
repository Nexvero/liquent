"""Datenanbindung für Liquent.

Spec: liquent/03_Data/Data_Source_Inventory.md
Nur Schnittstellen/Platzhalter — keine echten Netzwerk-Calls zu Börsen.
"""

from .sources import DataSource, HistoricalFileSource

__all__ = ["DataSource", "HistoricalFileSource"]
