"""iDRAC Power Monitor - CLI tool for Dell iDRAC power usage."""

__version__ = "0.1.0"

from .client import IDRACClient
from .power import get_power_metrics

__all__ = ["IDRACClient", "get_power_metrics"]
