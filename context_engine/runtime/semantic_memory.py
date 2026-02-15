from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher

WINDOW = 60
SIM_THRESHOLD = 0.72


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class MemoryItem:
    ts: float
    text: str


class WorkingMemory:
    def __init__(self):
        self.items = deque()

    def add(self, ts, text):
        self.items.append(MemoryItem(ts, text))

        while self.items and (ts - self.items[0].ts) > WINDOW:
            self.items.popleft()

    def nearest(self, text):
        best = None
        best_score = 0

        for item in self.items:
            s = similarity(text, item.text)
            if s > best_score:
                best_score = s
                best = item

        return best, best_score
