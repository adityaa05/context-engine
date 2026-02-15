from collections import deque, Counter
from dataclasses import dataclass
from math import log2

# -------- States --------
ORIENTING = "ORIENTING"
EXPLORING = "EXPLORING"
EXECUTING = "EXECUTING"
VERIFYING = "VERIFYING"
IDLE = "IDLE"


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


class CognitiveState:
    """
    Streaming cognitive phase detector.
    Consumes raw events continuously.
    """

    WINDOW = 40  # seconds of history
    EXEC_STABLE = 12  # execution threshold
    IDLE_THRESHOLD = 20  # idle cutoff

    def __init__(self):
        self.events = deque()
        self.last_state = None

    # ---------- PUBLIC ----------

    def process(self, event: Event):
        self._add_event(event)
        state = self._infer_state()

        if state != self.last_state:
            print(f"[STATE] {state}")
            self.last_state = state

    # ---------- INTERNAL ----------

    def _add_event(self, event):
        self.events.append(event)

        # remove old events outside window
        while self.events and event.ts - self.events[0].ts > self.WINDOW:
            self.events.popleft()

    # ---------- METRICS ----------

    def _switch_frequency(self):
        if len(self.events) < 2:
            return 0

        switches = 0
        prev = self.events[0].app + self.events[0].title

        for e in list(self.events)[1:]:
            cur = e.app + e.title
            if cur != prev:
                switches += 1
            prev = cur

        duration = self.events[-1].ts - self.events[0].ts
        return switches / max(duration, 1)

    def _anchor_stability(self):
        if not self.events:
            return 0

        last = self.events[-1]
        anchor = last.app + last.title

        stable_time = 0
        for e in reversed(self.events):
            if e.app + e.title == anchor:
                stable_time = last.ts - e.ts
            else:
                break

        return stable_time

    def _title_entropy(self):
        titles = [e.title for e in self.events if e.title]
        if not titles:
            return 0

        counts = Counter(titles)
        total = len(titles)

        entropy = 0
        for c in counts.values():
            p = c / total
            entropy -= p * log2(p)

        return entropy

    # ---------- STATE MACHINE ----------

    def _infer_state(self):
        if not self.events:
            return ORIENTING

        last = self.events[-1]

        # Idle
        if last.idle > self.IDLE_THRESHOLD:
            return IDLE

        stability = self._anchor_stability()
        switches = self._switch_frequency()
        entropy = self._title_entropy()

        # Execution
        if stability > self.EXEC_STABLE and switches < 0.02:
            return EXECUTING

        # Exploring
        if switches > 0.08 and entropy > 1.2:
            return EXPLORING

        # Verifying
        if switches > 0.08 and entropy <= 1.2:
            return VERIFYING

        return ORIENTING
