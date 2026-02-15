from collections import deque, Counter
from dataclasses import dataclass

WINDOW = 40
START_THRESHOLD = 8
STABLE = 0.6
BREAK = 0.35


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


class CognitiveSession:

    def __init__(self):
        self.events = deque(maxlen=WINDOW)
        self.active = False
        self.start_ts = None

    def process(self, e: Event):
        self.events.append(e)

        if len(self.events) < START_THRESHOLD:
            return

        stability = self._stability()

        if not self.active and stability > STABLE:
            self.active = True
            self.start_ts = self.events[0].ts
            print(f"\n[SESSION START] stable loop detected")

        elif self.active and stability < BREAK:
            duration = e.ts - self.start_ts
            print(f"[SESSION END] {duration:.1f}s instability")
            self.active = False

    def _stability(self):
        transitions = Counter()

        prev = None
        for e in self.events:
            if prev:
                transitions[(prev, e.app)] += 1
            prev = e.app

        if not transitions:
            return 0

        dominant = transitions.most_common(1)[0][1]
        total = sum(transitions.values())
        return dominant / total
