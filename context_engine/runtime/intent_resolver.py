from dataclasses import dataclass
from typing import Optional
import time


# ---------------- CONFIG ----------------

HARD_BREAK_SECONDS = 120
SOFT_BREAK_SECONDS = 35
DRIFT_TOLERANCE = 0.55


# ---------------- MODEL ----------------


@dataclass
class IntentState:
    anchor: str
    start_ts: float
    last_seen_ts: float
    drift_score: float = 0.0
    switches: int = 0


class IntentResolver:
    """
    Decides whether a LOOP_START begins a new episode
    or continues the same cognitive intent.
    """

    def __init__(self):
        self.current: Optional[IntentState] = None
        self.last_suspend_ts: Optional[float] = None

    # ---------- external signals ----------

    def notify_suspend(self, ts: float):
        self.last_suspend_ts = ts

    # ---------- decision ----------

    def resolve(self, ts: float, anchor: str) -> bool:
        """
        Returns True if NEW EPISODE
        Returns False if SAME EPISODE
        """

        if self.current is None:
            self.current = IntentState(anchor, ts, ts)
            return True

        # HARD BREAK — user mentally left
        if self.last_suspend_ts and (ts - self.last_suspend_ts < 6):
            self.current = IntentState(anchor, ts, ts)
            return True

        time_gap = ts - self.current.last_seen_ts

        # long silence → new task
        if time_gap > HARD_BREAK_SECONDS:
            self.current = IntentState(anchor, ts, ts)
            return True

        drift = self.semantic_drift(self.current.anchor, anchor)

        # smooth drift = thinking evolving
        if drift < DRIFT_TOLERANCE and time_gap < SOFT_BREAK_SECONDS:
            self.current.last_seen_ts = ts
            self.current.drift_score += drift
            return False

        # rapid topic jump
        if drift >= DRIFT_TOLERANCE and time_gap < 10:
            self.current.switches += 1
            if self.current.switches < 3:
                self.current.last_seen_ts = ts
                return False

        # new real task
        self.current = IntentState(anchor, ts, ts)
        return True

    # ---------- semantics ----------

    def semantic_drift(self, a: str, b: str) -> float:
        ta = set(a.split())
        tb = set(b.split())
        if not ta or not tb:
            return 1.0

        overlap = len(ta & tb) / max(len(ta), 1)
        return 1 - overlap
