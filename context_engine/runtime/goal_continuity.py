from collections import Counter
from typing import List, Optional
import math


SPECIALIZATION_WEIGHT = 2.2
OVERLAP_WEIGHT = 1.6
RETURN_WEIGHT = 1.4

NEW_EPISODE_THRESHOLD = 0.42
GOAL_MEMORY = 40


def tokenset(text: str) -> List[str]:
    return [t for t in text.lower().split() if len(t) > 2]


class GoalContinuity:

    def __init__(self):
        self.goal_tokens = Counter()
        self.last_anchor: Optional[str] = None
        self.last_app: Optional[str] = None

    # ---------- public ----------

    def is_same_goal(self, app: str, anchor: str) -> bool:

        tokens = tokenset(anchor)

        if not self.goal_tokens:
            self._absorb(tokens)
            self.last_anchor = anchor
            self.last_app = app
            return False  # first anchor always new episode

        overlap = self._overlap_score(tokens)
        specialization = self._specialization_score(tokens)
        return_bonus = self._return_bonus(app)

        continuity = (
            OVERLAP_WEIGHT * overlap
            + SPECIALIZATION_WEIGHT * specialization
            + RETURN_WEIGHT * return_bonus
        )

        self._absorb(tokens)
        self.last_anchor = anchor
        self.last_app = app

        return continuity >= NEW_EPISODE_THRESHOLD

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

        # decay memory
        if sum(self.goal_tokens.values()) > GOAL_MEMORY:
            for k in list(self.goal_tokens.keys()):
                self.goal_tokens[k] *= 0.85
