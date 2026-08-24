"""
alerts/__init__.py - Digital Twin CO2 Monitor (DTCM)
=====================================================
The ``alerts`` package provides the Alert Manager for DTCM.

Public surface:
    * AlertManager   - evaluates every incoming EnvironmentalData row against
                       per-zone thresholds, deduplicates and auto-resolves
                       alerts, pushes SSE events, and optionally sends e-mail
                       notifications.
    * alert_manager  - application-level singleton; no special initialisation
                       is required beyond importing the module.
"""

from alerts.manager import AlertManager, alert_manager  # noqa: F401

__all__ = ["AlertManager", "alert_manager"]

