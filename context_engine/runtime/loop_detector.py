from collections import deque, Counter
from dataclasses import dataclass
from typing import Deque, Optional, Tuple, List
import math
import re

# ---------------- EVENT ----------------


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


# ---------------- PARAMETERS ----------------

WINDOW = 60
ANCHOR_CONFIRM = 4
STATE_MEMORY = 8


# ---------------- TOKENIZATION ----------------

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


# ---------------- LOOP DETECTOR ----------------


class LoopDetector:

    def __init__(self) -> None:

        # recent events memory
        self.memory: Deque[Tuple[float, List[str]]] = deque()

        # adaptive vocabulary statistics
        self.global_freq: Counter[str] = Counter()
        self.total_tokens: int = 0

        # attractor
        self.anchor_hits = 0
        self.anchor_text: Optional[str] = None

        # cognitive state
        self.prev_idle: Optional[float] = None
        self.idle_resets: Deque[bool] = deque(maxlen=STATE_MEMORY)
        self.state: Optional[str] = None

    # ---------------- PROCESS ----------------

    def process(self, e: Event) -> None:
        self.update_state(e)
        self.detect_loop(e)

    # ---------------- STATE MODEL ----------------

    def update_state(self, e: Event) -> None:

        if self.prev_idle is None:
            self.prev_idle = e.idle
            return

        delta = self.prev_idle - e.idle
        self.prev_idle = e.idle

        reset = delta > 1.5 and e.idle < 0.3
        self.idle_resets.append(reset)

        if len(self.idle_resets) < 5:
            return

        ratio = sum(self.idle_resets) / len(self.idle_resets)

        if e.idle > 15:
            new_state = "AWAY"
        elif ratio > 0.45:
            new_state = "EXECUTING"
        elif ratio > 0.15:
            new_state = "SCANNING"
        else:
            new_state = "ABSORBED"

        if new_state != self.state:
            self.state = new_state
            print(f"[STATE] {self.state}")

    # ---------------- SIMILARITY ----------------

    def weighted_similarity(self, a: List[str], b: List[str]) -> float:

        if not a or not b:
            return 0.0

        shared = set(a) & set(b)
        if not shared:
            return 0.0

        score = 0.0
        norm = 0.0

        for token in shared:
            # inverse frequency weighting (automatic noise removal)
            freq = self.global_freq[token] / max(1, self.total_tokens)
            weight = 1.0 / (1.0 + 10 * freq)

            score += weight
            norm += weight

        return score / max(norm, 1e-6)

    # ---------------- LOOP MODEL ----------------

    def detect_loop(self, e: Event) -> None:

        text = f"{e.app} {e.title}"
        tokens = tokenize(text)

        if not tokens:
            return

        # update vocabulary stats
        for t in tokens:
            self.global_freq[t] += 1
            self.total_tokens += 1

        # add memory
        self.memory.append((e.ts, tokens))

        # expire memory
        while self.memory and (e.ts - self.memory[0][0]) > WINDOW:
            self.memory.popleft()

        # find recurrence
        best_score = 0.0
        best_match: Optional[List[str]] = None

        for _, past in self.memory:
            if past == tokens:
                continue

            s = self.weighted_similarity(tokens, past)

            if s > best_score:
                best_score = s
                best_match = past

        # dynamic recurrence
        if best_score > 0.35:
            self.anchor_hits += 1
        elif len(self.memory) > 5:
            self.anchor_hits *= 0.8

        # loop start
        if self.anchor_hits >= ANCHOR_CONFIRM and best_match:
            if self.anchor_text != " ".join(best_match):
                self.anchor_text = " ".join(best_match)
                print(f"\n[LOOP START] {' '.join(tokens[:8])}")

        # loop end
        if self.anchor_text and self.anchor_hits < 1:
            print("[LOOP END]")
            self.anchor_text = None
