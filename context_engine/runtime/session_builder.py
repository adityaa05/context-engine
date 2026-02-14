from dataclasses import dataclass, field
from collections import Counter
import time

IDLE_BREAK = 180
SOFT_SWITCH_WINDOW = 25


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


@dataclass
class Session:
    start: float
    last: float
    apps: Counter = field(default_factory=Counter)


class SessionBuilder:
    def __init__(self):
        self.current = None
        self.last_event = None

    def process(self, e: Event):
        # 1. Hard break: idle
        if e.idle > IDLE_BREAK:
            self._end("Idle Break")
            return

        # 2. First event
        if self.current is None:
            self.current = Session(e.ts, e.ts)
            self.current.apps[e.app] += 1
            self.last_event = e
            print(f"\n[START] {e.app}")
            return

        # 3. Time gap
        gap = e.ts - self.last_event.ts
        if gap > IDLE_BREAK:
            self._end("Time Gap")
            self._start_new(e)
            return

        # 4. Soft switch detection
        if e.app not in self.current.apps and gap > SOFT_SWITCH_WINDOW:
            self._end("Context Shift")
            self._start_new(e)
            return

        # Continue session
        self.current.apps[e.app] += 1
        self.current.last = e.ts
        self.last_event = e

    def _start_new(self, e):
        self.current = Session(e.ts, e.ts)
        self.current.apps[e.app] += 1
        self.last_event = e
        print(f"\n[START] {e.app}")

    def _end(self, reason):
        if not self.current:
            return
        duration = self.current.last - self.current.start
        top = ", ".join(a for a, _ in self.current.apps.most_common(3))
        print(f"\n[END] {duration:.1f}s | {top} | {reason}")
        self.current = None
