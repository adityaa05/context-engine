from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Deque, Optional, Tuple


# -------- EVENT --------


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


# -------- PARAMETERS --------

WINDOW = 60  # working memory seconds
SIM_THRESHOLD = 0.72  # semantic similarity for recurrence
ANCHOR_CONFIRM = 4  # hits to form attractor


# -------- SIMILARITY --------


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# -------- LOOP DETECTOR --------


class LoopDetector:

    def __init__(self) -> None:
        # working memory of recent thoughts
        self.memory: Deque[Tuple[float, str]] = deque()

        # active attractor
        self.anchor_text: Optional[str] = None
        self.anchor_hits: int = 0

        # cognition state tracking
        self.prev_idle: Optional[float] = None
        self.idle_resets: Deque[bool] = deque(maxlen=8)
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

    # ---------------- LOOP MODEL ----------------

    def detect_loop(self, e: Event) -> None:

        text = f"{e.app} {e.title}".strip()

        if not text:
            return

        # add memory
        self.memory.append((e.ts, text))

        # remove expired memory
        while self.memory and (e.ts - self.memory[0][0]) > WINDOW:
            self.memory.popleft()

        # find recurrence
        best_score = 0.0
        best_text: Optional[str] = None

        for _, past in self.memory:
            if past == text:
                continue

            s = similarity(text, past)
            if s > best_score:
                best_score = s
                best_text = past

        # recurrence detected
        if best_score > SIM_THRESHOLD:
            self.anchor_hits += 1
        else:
            self.anchor_hits = max(0, self.anchor_hits - 1)

        # form attractor
        if (
            self.anchor_hits >= ANCHOR_CONFIRM
            and best_text
            and self.anchor_text != best_text
        ):
            self.anchor_text = best_text
            print(f"\n[LOOP START] {text}")

        # collapse attractor
        if self.anchor_text and self.anchor_hits == 0:
            print("[LOOP END]")
            self.anchor_text = None
