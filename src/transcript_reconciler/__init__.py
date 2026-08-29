"""Utilities for reconciling multiple transcripts of one meeting."""

from .config import SegmentOverride, SessionConfig, load_config
from .pipeline import ReconcileResult, reconcile

__all__ = [
    "ReconcileResult",
    "SegmentOverride",
    "SessionConfig",
    "load_config",
    "reconcile",
]
__version__ = "0.1.0"
