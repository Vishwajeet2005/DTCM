"""
twin/__init__.py - Digital Twin CO2 Monitor (DTCM)
===================================================
The ``twin`` package implements the Digital Twin Engine for DTCM.

Public surface:
    * DigitalTwinEngine  - maintains a real-time virtual state of all sensor
                           zones, handles scenario simulation, and drives the
                           background state-synchronisation thread.
    * twin_engine        - application-level singleton; import and call
                           ``twin_engine.init_app(app)`` during Flask startup.
"""

from twin.engine import DigitalTwinEngine, twin_engine  # noqa: F401

__all__ = ["DigitalTwinEngine", "twin_engine"]

