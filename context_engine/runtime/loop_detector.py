from collections import deque, Counter
from dataclasses import dataclass
import time
from dataclasses import dataclass


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


WINDOW = 45  # working memory window (seconds)
ANCHOR_THRESHOLD = 3  # returns needed to confirm a loop


class LoopDetector:
    def __init__(self):
        self.buffer = deque()
        self.anchor = None
        self.last_state = None

    def process(self, e):
        self.buffer.append(e)

        # remove old events outside working memory
        while self.buffer and (e.ts - self.buffer[0].ts) > WINDOW:
            self.buffer.popleft()

        self.detect_loop(e)

    def detect_loop(self, e):
        apps = [ev.app for ev in self.buffer]
        freq = Counter(apps)

        top_app, count = freq.most_common(1)[0]

        # loop established
        if count >= ANCHOR_THRESHOLD:
            if self.anchor != top_app:
                self.anchor = top_app
                print(f"\n[LOOP START] {top_app}")

        # loop collapse
        elif self.anchor and top_app != self.anchor:
            print(f"[LOOP END] {self.anchor}")
            self.anchor = None
