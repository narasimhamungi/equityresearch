"""EquityResearch: initiation-of-coverage layer over Trellis and ValuationLab.

Adds what the upstream repos do not have: time-varying Bull/Base/Bear driver
schedules (scenarios.py) and a diluted share count (shares.py), which is the
denominator every per-share number in an initiation report depends on.
"""

__version__ = "0.1.0"
