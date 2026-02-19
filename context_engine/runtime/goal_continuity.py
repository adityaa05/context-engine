from collections import Counter
from typing import List, Optional
import math


# ---------------- PARAMETERS ----------------

GOAL_MEMORY = 60

BASE_SILENCE_DECAY = 0.6
OVERLAP_REINFORCE = 1.2
SPECIALIZATION_REINFORCE = 0.8
DRIFT_PENALTY = 0.9
RESEARCH_FORGIVENESS = 0.65
MATURITY_BONUS = 0.25

NEW_EPISODE_THRESHOLD = 0.40


# ---------------- TOKENIZE ----------------


def tokenset(text: str) -> List[str]:
    return [t for t in text.lower().split() if len(t) > 2]


# ---------------- GOAL CONTINUITY ----------------


class GoalContinuity:

    def __init__(self):
        self.goal_tokens = Counter()

        self.last_anchor: Optional[str] = None
        self.last_app: Optional[str] = None
        self.last_ts: Optional[float] = None

        self.episode_start_ts: Optional[float] = None

        self.goal_strength: float = 0.0
        self.loop_count: int = 0
        self.research_hops: int = 0

    # ---------- PUBLIC ----------

    def is_same_goal(self, app: str, anchor: str, ts: float) -> bool:

        tokens = tokenset(anchor)

        # FIRST EVER ANCHOR → NEW EPISODE
        if not self.goal_tokens:
            self._start_new_episode(app, anchor, tokens, ts)
            return False

        time_gap = ts - (self.last_ts or ts)
        episode_duration = (self.last_ts or ts) - (self.episode_start_ts or ts)

        # ---------- 1. SILENCE DECAY ----------
        dynamic_timeout = min(60.0 + (episode_duration / 600.0) * 30.0, 300.0)
        silence_decay = min(time_gap / dynamic_timeout, 1.5) * BASE_SILENCE_DECAY

        # ---------- 2. SEMANTIC SCORES ----------
        overlap = self._overlap_score(tokens)
        specialization = self._specialization_score(tokens)

        semantic_reinforcement = (
            OVERLAP_REINFORCE * overlap + SPECIALIZATION_REINFORCE * specialization
        )

        drift_penalty = (1 - overlap) * DRIFT_PENALTY

        # ---------- 3. RESEARCH FORGIVENESS ----------
        if time_gap < 8 and self.loop_count > 5:
            drift_penalty *= RESEARCH_FORGIVENESS
            self.research_hops += 1

        # ---------- 4. MATURITY BONUS ----------
        maturity_bonus = min(self.loop_count / 10.0, 1.0) * MATURITY_BONUS

        # ---------- UPDATE GOAL STRENGTH ----------
        self.goal_strength += semantic_reinforcement
        self.goal_strength -= drift_penalty
        self.goal_strength -= silence_decay
        self.goal_strength += maturity_bonus

        self.goal_strength = max(0.0, min(2.0, self.goal_strength))

        # ---------- DECISION ----------
        if self.goal_strength < NEW_EPISODE_THRESHOLD:
            self._start_new_episode(app, anchor, tokens, ts)
            return False

        # SAME EPISODE
        self._absorb(tokens)
        self.last_anchor = anchor
        self.last_app = app
        self.last_ts = ts
        self.loop_count += 1

        return True

    # ---------- INTERNAL ----------

    def _start_new_episode(self, app: str, anchor: str, tokens: List[str], ts: float):
        self.goal_tokens.clear()
        self.goal_strength = 1.0
        self.loop_count = 1
        self.research_hops = 0

        self.episode_start_ts = ts
        self.last_ts = ts
        self.last_anchor = anchor
        self.last_app = app

        self._absorb(tokens)

    def _overlap_score(self, tokens: List[str]) -> float:
        shared = sum(self.goal_tokens[t] for t in tokens if t in self.goal_tokens)
        total = sum(self.goal_tokens.values()) + 1
        return shared / total

    def _specialization_score(self, tokens: List[str]) -> float:
        new_tokens = [t for t in tokens if t not in self.goal_tokens]
        return math.tanh(len(new_tokens) / 6)

    def _absorb(self, tokens: List[str]):
        for t in tokens:
            self.goal_tokens[t] += 1

        # decay memory
        if sum(self.goal_tokens.values()) > GOAL_MEMORY:
            for k in list(self.goal_tokens.keys()):
                self.goal_tokens[k] *= 0.85
