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
ANCHOR_CONFIRM = 4
STATE_MEMORY = 12

ATTENTION_MAX = 100
ATTENTION_DECAY_PASSIVE = 2
ATTENTION_DECAY_DETACHED = 8
ATTENTION_GAIN_ACTIVE = 6
ATTENTION_GAIN_RELATED = 3
LOOP_END_THRESHOLD = 0


# ---------------- TOKENIZATION ----------------

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def state_key(app: str, title: str) -> str:
    """Normalize an interaction state into a cognitive key."""
    tokens = tokenize(f"{app} {title}")
    return " ".join(tokens[:6])  # small stable signature


# ---------------- LOOP DETECTOR ----------------


class LoopDetector:

    def __init__(self) -> None:

        self.memory: Deque[Tuple[float, List[str]]] = deque()
        self.global_freq: Counter[str] = Counter()
        self.total_tokens: int = 0

        self.anchor_hits = 0
        self.anchor_text: Optional[str] = None

        self.prev_idle: Optional[float] = None
        self.micro_buffer: Deque[str] = deque(maxlen=STATE_MEMORY)
        self.phase: Optional[str] = None

        # cognitive gravity
        self.attention_score = 0

        # basin (interaction attractor)
        self.basin: Counter[str] = Counter()

        # reentry system
        self.suspended = False
        self.last_anchor_before_sleep: Optional[str] = None
        self.reentry = ReentryClassifier()

    # ---------------- BASIN SIMILARITY ----------------

    def basin_similarity(self, key: str) -> bool:
        """Detect return to same mental basin (not string match, behavior match)."""

        if key in self.basin:
            return True

        # soft overlap similarity
        key_tokens = set(key.split())

        for existing in self.basin:
            overlap = len(key_tokens & set(existing.split()))
            if overlap >= 2:
                return True

        return False

    # ---------------- PROCESS ----------------

    def process(self, e: Event) -> None:

        # ---------- SUSPEND ----------
        if not self.suspended and e.idle > 25:
            self.suspended = True
            self.last_anchor_before_sleep = self.anchor_text
            print("\n[SUSPEND]")

        if self.suspended and e.idle < 0.5:
            self.suspended = False
            self.reentry.start(e.ts, self.last_anchor_before_sleep)

        # ---------- REENTRY CONTINUITY ----------
        key = state_key(e.app, e.title)

        similar = self.basin_similarity(key)

        reset = False
        if self.prev_idle is not None:
            reset = (self.prev_idle - e.idle) > 1.5 and e.idle < 0.3

        verdict = self.reentry.observe(e.ts, key, similar, reset)

        if verdict:
            self.attention_score = 40  # restore gravity after reentry

        # ignore loop detection during reconstruction
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

        if self.anchor_text:
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
                self.anchor_text = None
                self.basin.clear()

    # ---------------- LOOP MODEL ----------------

    def detect_loop(self, e: Event) -> None:

        key = state_key(e.app, e.title)

        if not key.strip():
            return

        # grow basin
        self.basin[key] += 1

        # anchor formation
        if self.basin[key] >= ANCHOR_CONFIRM:
            if self.anchor_text != key:
                self.anchor_text = key
                self.attention_score = 60
                print(f"\n[LOOP START] {key}")
