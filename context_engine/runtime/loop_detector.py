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

WINDOW = 90
ANCHOR_CONFIRM = 5
STATE_MEMORY = 12

TOPIC_SIM_THRESHOLD = 0.22
TOPIC_SHIFT_THRESHOLD = 0.12
TOPIC_DECAY = 0.97

ATTENTION_MAX = 100
ATTENTION_DECAY = 3
ATTENTION_GAIN = 6


# ---------------- TOKENIZATION ----------------

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


# ---------------- LOOP DETECTOR ----------------


class LoopDetector:

    def __init__(self, bus):

        self.bus = bus

        self.memory: Deque[Tuple[float, List[str]]] = deque()
        self.topic_vector: Counter[str] = Counter()

        self.anchor_hits = 0
        self.anchor_text: Optional[str] = None

        self.prev_idle: Optional[float] = None
        self.micro_buffer: Deque[str] = deque(maxlen=STATE_MEMORY)
        self.phase: Optional[str] = None

        self.attention_score = 0

        self.suspended = False
        self.last_anchor_before_sleep: Optional[str] = None
        self.reentry = ReentryClassifier()

    # ---------------- PROCESS ----------------

    def process(self, e: Event) -> None:

        # suspend detection
        if not self.suspended and e.idle > 25:
            self.suspended = True
            self.last_anchor_before_sleep = self.anchor_text
            self.bus.emit_suspend(e.ts)

        if self.suspended and e.idle < 0.5:
            self.suspended = False
            self.reentry.start(e.ts, self.last_anchor_before_sleep)

        semantic_now = f"{e.app} {e.title}".lower()

        similar = (
            self.last_anchor_before_sleep
            and self.last_anchor_before_sleep in semantic_now
        )

        reset = False
        if self.prev_idle is not None:
            reset = (self.prev_idle - e.idle) > 1.5 and e.idle < 0.3

        verdict = self.reentry.observe(e.ts, semantic_now, similar, reset)

        if verdict:
            self.attention_score = 40
            self.bus.emit_reentry(e.ts, verdict)

        if self.reentry.active:
            self.prev_idle = e.idle
            return

        self.update_state(e)
        self.detect_topic_loop(e)

    # ---------------- STATE ----------------

    def update_state(self, e: Event):

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
            self.bus.emit_phase(e.ts, new_phase)

        if self.anchor_text:
            if new_phase == "DETACHED":
                self.attention_score -= ATTENTION_DECAY
            else:
                self.attention_score += ATTENTION_GAIN

            self.attention_score = max(0, min(ATTENTION_MAX, self.attention_score))

            if self.attention_score <= 0:
                self.bus.emit_loop_end(e.ts, self.anchor_text)
                self.anchor_text = None
                self.topic_vector.clear()

    # ---------------- TOPIC SIMILARITY ----------------

    def topic_similarity(self, tokens: List[str]) -> float:
        if not self.topic_vector:
            return 0.0

        score = 0
        for t in tokens:
            if t in self.topic_vector:
                score += self.topic_vector[t]

        norm = sum(self.topic_vector.values()) + 1e-6
        return score / norm

    # ---------------- LOOP MODEL ----------------

    def detect_topic_loop(self, e: Event):

        text = f"{e.app} {e.title}"
        tokens = tokenize(text)

        if not tokens:
            return

        similarity = self.topic_similarity(tokens)

        # reinforce current topic
        if similarity > TOPIC_SIM_THRESHOLD:
            self.anchor_hits += 1
            for t in tokens:
                self.topic_vector[t] += 1

        # possible shift
        else:
            self.anchor_hits -= 1
            if similarity < TOPIC_SHIFT_THRESHOLD:
                for k in list(self.topic_vector):
                    self.topic_vector[k] *= TOPIC_DECAY

        # start loop
        if self.anchor_text is None and self.anchor_hits >= ANCHOR_CONFIRM:
            self.anchor_text = " ".join(tokens[:6])
            self.attention_score = 60
            self.bus.emit_loop_start(e.ts, self.anchor_text)
