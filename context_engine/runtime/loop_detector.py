from collections import deque, Counter
from dataclasses import dataclass
from typing import Deque, Optional, Tuple, List
import re

from .reentry_classifier import ReentryClassifier
from .event_bus import EventBus


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

ANCHOR_STARVATION_TIME = 18


# ---------------- TOKENIZATION ----------------

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


# ---------------- LOOP DETECTOR ----------------


class LoopDetector:

    def __init__(self, bus: EventBus):

        self.bus = bus

        self.memory: Deque[Tuple[float, List[str]]] = deque()
        self.global_freq: Counter[str] = Counter()
        self.total_tokens: int = 0

        self.anchor_hits = 0
        self.anchor_text: Optional[str] = None

        self.prev_idle: Optional[float] = None
        self.micro_buffer: Deque[str] = deque(maxlen=STATE_MEMORY)
        self.phase: Optional[str] = None

        self.attention_score = 0

        # reentry
        self.suspended = False
        self.last_anchor_before_sleep: Optional[str] = None
        self.reentry = ReentryClassifier()

        # semantic suspend tracking
        self.last_anchor_seen_ts: Optional[float] = None
        self.starving_since: Optional[float] = None

    # ---------------- PROCESS ----------------

    def process(self, e: Event) -> None:

        # wake from suspend
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
            self.bus.emit_reentry(e.ts, verdict)

        if self.reentry.active:
            self.prev_idle = e.idle
            return

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
            self.bus.emit_phase(e.ts, new_phase)

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
                self.anchor_text = None

    # ---------------- FIXED SEMANTIC SUSPEND ----------------

    def check_semantic_suspend(self, e: Event, tokens: List[str]):

        if not self.anchor_text:
            return

        anchor_tokens = set(self.anchor_text.split())
        token_set = set(tokens)

        overlap = len(anchor_tokens & token_set) / max(len(anchor_tokens), 1)
        similar = overlap > 0.35

        same_app = self.anchor_text.startswith(e.app.lower())

        # STILL SAME ENVIRONMENT → NEVER SUSPEND
        if similar or same_app:
            self.last_anchor_seen_ts = e.ts
            self.starving_since = None
            return

        # REAL STARVATION
        if self.last_anchor_seen_ts is None:
            self.last_anchor_seen_ts = e.ts
            return

        if self.starving_since is None:
            self.starving_since = e.ts
            return

        starvation = e.ts - self.starving_since

        # ONLY DETACH IF USER IS ACTUALLY DETACHED
        if starvation > ANCHOR_STARVATION_TIME and self.phase == "DETACHED":
            self.trigger_suspend(e.ts)

    def trigger_suspend(self, ts: float):

        if self.suspended:
            return

        self.suspended = True
        self.last_anchor_before_sleep = self.anchor_text
        self.anchor_text = None
        self.anchor_hits = 0
        self.attention_score = 0

        self.bus.emit_suspend(ts)

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

        self.check_semantic_suspend(e, tokens)

        for t in tokens:
            self.global_freq[t] += 1
            self.total_tokens += 1

        self.memory.append((e.ts, tokens))

        while self.memory and (e.ts - self.memory[0][0]) > WINDOW:
            self.memory.popleft()

        best_score = 0.0
        best_match: Optional[List[str]] = None

        for _, past in self.memory:
            if past == tokens:
                continue

            s = self.weighted_similarity(tokens, past)

            if s > best_score:
                best_score = s
                best_match = past

        if best_score > 0.35:
            self.anchor_hits += 1
        else:
            self.anchor_hits *= 0.9

        if self.anchor_hits >= ANCHOR_CONFIRM and best_match:
            new_anchor = " ".join(best_match)

            if self.anchor_text != new_anchor:
                self.anchor_text = new_anchor
                self.attention_score = 60
                self.last_anchor_seen_ts = e.ts
                self.bus.emit_loop_start(e.ts, new_anchor)
