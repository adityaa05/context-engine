from collections import deque, Counter
from dataclasses import dataclass
from typing import Deque, Optional, Tuple, List
import re

from .reentry_classifier import ReentryClassifier


# ---------------- EVENT ----------------


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


# ---------------- PARAMETERS ----------------

WINDOW = 60
STATE_MEMORY = 12

ATTENTION_MAX = 100
ATTENTION_DECAY_PASSIVE = 2
ATTENTION_DECAY_DETACHED = 8
ATTENTION_GAIN_ACTIVE = 6
ATTENTION_GAIN_RELATED = 3
LOOP_END_THRESHOLD = 0

# Basin physics
CLUSTER_WINDOW = 90
ESCAPE_VELOCITY = 0.55
MIN_REVISITS = 4


# ---------------- TOKENIZATION ----------------

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def state_key(app: str, title: str) -> str:
    text = f"{app} {title}".lower()
    tokens = tokenize(text)
    return " ".join(tokens[:6])  # compressed identity


# ---------------- BASIN MODEL ----------------


class Basin:
    def __init__(self):
        self.events: Deque[Tuple[float, str]] = deque()
        self.counts: Counter[str] = Counter()
        self.active = False

    def update(self, ts: float, key: str):
        self.events.append((ts, key))
        self.counts[key] += 1

        while self.events and ts - self.events[0][0] > CLUSTER_WINDOW:
            _, old_key = self.events.popleft()
            self.counts[old_key] -= 1
            if self.counts[old_key] <= 0:
                del self.counts[old_key]

    def cluster_size(self):
        return len(self.counts)

    def revisits(self):
        return sum(v - 1 for v in self.counts.values() if v > 1)

    def novelty_ratio(self):
        if not self.events:
            return 1.0
        return self.cluster_size() / len(self.events)


# ---------------- LOOP DETECTOR ----------------


class LoopDetector:

    def __init__(self) -> None:

        self.prev_idle: Optional[float] = None
        self.micro_buffer: Deque[str] = deque(maxlen=STATE_MEMORY)
        self.phase: Optional[str] = None

        self.attention_score = 0

        # basin model replaces anchor
        self.basin = Basin()

        # reentry system
        self.suspended = False
        self.last_anchor_before_sleep: Optional[str] = None
        self.reentry = ReentryClassifier()

    # ---------------- PROCESS ----------------

    def process(self, e: Event) -> None:

        # ---------- SUSPEND ----------
        if not self.suspended and e.idle > 25:
            self.suspended = True
            print("\n[SUSPEND]")

        if self.suspended and e.idle < 0.5:
            self.suspended = False
            self.reentry.start(e.ts, None)

        semantic_now = f"{e.app} {e.title}".lower()

        reset = False
        if self.prev_idle is not None:
            reset = (self.prev_idle - e.idle) > 1.5 and e.idle < 0.3

        verdict = self.reentry.observe(e.ts, semantic_now, False, reset)

        if verdict:
            self.attention_score = 40

        if self.reentry.active:
            self.prev_idle = e.idle
            return

        # ---------- NORMAL ----------
        self.update_state(e)
        self.detect_loop(e)

    # ---------------- STATE ----------------

    def update_state(self, e: Event) -> None:

        if self.prev_idle is None:
            self.prev_idle = e.idle
            return

        delta = self.prev_idle - e.idle
        self.prev_idle = e.idle

        reset = delta > 1.5 and e.idle < 0.3

        if e.idle > 20:
            micro = "DETACHED"
        elif reset:
            micro = "ACTIVE"
        else:
            micro = "PASSIVE"

        self.micro_buffer.append(micro)

        if len(self.micro_buffer) < 8:
            return

        active = self.micro_buffer.count("ACTIVE")
        passive = self.micro_buffer.count("PASSIVE")
        detached = self.micro_buffer.count("DETACHED")

        if detached >= 6:
            new_phase = "DETACHED"
        elif active >= 6:
            new_phase = "EXPLORING"
        elif passive >= 6:
            new_phase = "STABLE"
        else:
            new_phase = "ENTERING"

        if new_phase != self.phase:
            self.phase = new_phase
            print(f"[PHASE] {self.phase}")

        # -------- ATTENTION PHYSICS --------

        if self.basin.active:
            if new_phase == "ACTIVE":
                self.attention_score += ATTENTION_GAIN_ACTIVE
            elif new_phase == "EXPLORING":
                self.attention_score += ATTENTION_GAIN_RELATED
            elif new_phase == "PASSIVE":
                self.attention_score -= ATTENTION_DECAY_PASSIVE
            elif new_phase == "DETACHED":
                self.attention_score -= ATTENTION_DECAY_DETACHED

            self.attention_score = max(0, min(ATTENTION_MAX, self.attention_score))

            if self.attention_score <= LOOP_END_THRESHOLD:
                print("[LOOP END]")
                self.basin.active = False

    # ---------------- LOOP MODEL (BASIN) ----------------

    def detect_loop(self, e: Event) -> None:

        key = state_key(e.app, e.title)
        self.basin.update(e.ts, key)

        size = self.basin.cluster_size()
        revisits = self.basin.revisits()
        novelty = self.basin.novelty_ratio()

        stable = revisits >= MIN_REVISITS and novelty < ESCAPE_VELOCITY

        if stable and not self.basin.active:
            self.basin.active = True
            self.attention_score = 60
            print(f"\n[LOOP START] {key}")

        if self.basin.active and novelty > ESCAPE_VELOCITY:
            self.basin.active = False
            print("[LOOP END]")
