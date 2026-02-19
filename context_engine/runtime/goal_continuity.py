from collections import Counter
from typing import List, Optional
import math

# --- PARAMETERS ---
NEW_EPISODE_THRESHOLD = 0.42
GOAL_MEMORY = 40
RETURN_WINDOW = 90  # seconds allowed to come back to original goal
PROVISIONAL_TIMEOUT = 25  # browsing window before we commit new episode


def tokenset(text: str) -> List[str]:
    return [t for t in text.lower().split() if len(t) > 2]


class GoalContinuity:
    """
    Now supports provisional episodes:
    We DO NOT immediately break goal when anchor changes.
    We wait to see if user returns (research loop behaviour).
    """

    def __init__(self):
        self.goal_tokens = Counter()
        self.last_anchor: Optional[str] = None
        self.last_app: Optional[str] = None
        self.last_ts: Optional[float] = None

        # provisional tracking
        self.pending_anchor: Optional[str] = None
        self.pending_ts: Optional[float] = None

    # ---------- public ----------

    def is_same_goal(self, app: str, anchor: str, ts: float) -> bool:

        tokens = tokenset(anchor)

        # first anchor always new
        if not self.goal_tokens:
            self._commit(anchor, app, tokens, ts)
            return False

        # ---------- RETURN CHECK ----------
        if self.pending_anchor:
            # returned to original goal -> cancel provisional break
            if self._semantic_match(anchor, self.last_anchor):
                self.pending_anchor = None
                self.pending_ts = None
                self._commit(anchor, app, tokens, ts)
                return True

            # waited too long -> commit new episode
            if ts - self.pending_ts > PROVISIONAL_TIMEOUT:
                self._reset(tokens)
                self._commit(anchor, app, tokens, ts)
                return False

            # still exploring
            return True

        # ---------- SEMANTIC CONTINUITY ----------
        continuity = self._continuity_score(app, tokens)

        if continuity >= NEW_EPISODE_THRESHOLD:
            self._commit(anchor, app, tokens, ts)
            return True

        # ---------- POSSIBLE NEW GOAL ----------
        self.pending_anchor = anchor
        self.pending_ts = ts
        return True

    # ---------- scoring ----------

    def _continuity_score(self, app: str, tokens: List[str]) -> float:
        overlap = self._overlap_score(tokens)
        specialization = self._specialization_score(tokens)
        return_bonus = self._return_bonus(app)

        return 1.6 * overlap + 2.2 * specialization + 1.4 * return_bonus

    def _semantic_match(self, a: Optional[str], b: Optional[str]) -> bool:
        if not a or not b:
            return False
        at = set(tokenset(a))
        bt = set(tokenset(b))
        return len(at & bt) / max(len(at), 1) > 0.35

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

    # ---------- state ----------

    def _commit(self, anchor: str, app: str, tokens: List[str], ts: float):
        self.last_anchor = anchor
        self.last_app = app
        self.last_ts = ts
        self._absorb(tokens)

    def _reset(self, tokens: List[str]):
        self.goal_tokens = Counter(tokens)

    def _absorb(self, tokens: List[str]):
        for t in tokens:
            self.goal_tokens[t] += 1

        if sum(self.goal_tokens.values()) > GOAL_MEMORY:
            for k in list(self.goal_tokens.keys()):
                self.goal_tokens[k] *= 0.85
