from collections import Counter
from typing import List, Optional
import math


SPECIALIZATION_WEIGHT = 2.2
OVERLAP_WEIGHT = 1.6
RETURN_WEIGHT = 1.4

NEW_EPISODE_THRESHOLD = 0.42
GOAL_MEMORY = 40

# ---- temporal cognition ----
HARD_BREAK_SECONDS = 120
SOFT_BREAK_SECONDS = 12
SCAN_WINDOW_SECONDS = 8
SCAN_TOLERANCE = 3


def tokenset(text: str) -> List[str]:
    return [t for t in text.lower().split() if len(t) > 2]


class GoalContinuity:

    def __init__(self):
        self.goal_tokens = Counter()
        self.last_anchor: Optional[str] = None
        self.last_app: Optional[str] = None
        self.last_ts: Optional[float] = None

        # scanning memory
        self.recent_switches = 0

    # ---------- public ----------

    def is_same_goal(self, app: str, anchor: str, ts: float) -> bool:

        tokens = tokenset(anchor)

        # first anchor
        if not self.goal_tokens:
            self._absorb(tokens)
            self.last_anchor = anchor
            self.last_app = app
            self.last_ts = ts
            return False

        # ---------- TIME CHECK ----------
        gap = ts - self.last_ts if self.last_ts else 0

        if gap > HARD_BREAK_SECONDS:
            self._reset(tokens, app, ts)
            return False

        # ---------- SEMANTIC ----------
        overlap = self._overlap_score(tokens)
        specialization = self._specialization_score(tokens)
        return_bonus = self._return_bonus(app)

        continuity = (
            OVERLAP_WEIGHT * overlap
            + SPECIALIZATION_WEIGHT * specialization
            + RETURN_WEIGHT * return_bonus
        )

        # ---------- SCANNING TOLERANCE ----------
        if continuity < NEW_EPISODE_THRESHOLD:
            if gap < SCAN_WINDOW_SECONDS:
                self.recent_switches += 1
                if self.recent_switches <= SCAN_TOLERANCE:
                    self._absorb(tokens)
                    self.last_anchor = anchor
                    self.last_app = app
                    self.last_ts = ts
                    return True
            else:
                self.recent_switches = 0

        # ---------- DECISION ----------
        same = continuity >= NEW_EPISODE_THRESHOLD

        if not same and gap < SOFT_BREAK_SECONDS:
            same = True

        # update memory
        self._absorb(tokens)
        self.last_anchor = anchor
        self.last_app = app
        self.last_ts = ts

        return same

    # ---------- scoring ----------

    def _overlap_score(self, tokens: List[str]) -> float:
        shared = sum(self.goal_tokens[t] for t in tokens if t in self.goal_tokens)
        total = sum(self.goal_tokens.values()) + 1
        return shared / total

    def _specialization_score(self, tokens: List[str]) -> float:
        new_tokens = [t for t in tokens if t not in self.goal_tokens]
        return math.tanh(len(new_tokens) / 6)

    def _return_bonus(self, app: str) -> float:
        if self.last_app and self.last_app != app:
            return 0.7
        return 0.0

    # ---------- update ----------

    def _absorb(self, tokens: List[str]):
        for t in tokens:
            self.goal_tokens[t] += 1

        if sum(self.goal_tokens.values()) > GOAL_MEMORY:
            for k in list(self.goal_tokens.keys()):
                self.goal_tokens[k] *= 0.85

    def _reset(self, tokens: List[str], app: str, ts: float):
        self.goal_tokens.clear()
        self.recent_switches = 0
        self._absorb(tokens)
        self.last_anchor = anchor = " ".join(tokens)
        self.last_app = app
        self.last_ts = ts
