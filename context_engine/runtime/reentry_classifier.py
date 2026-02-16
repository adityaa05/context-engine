from typing import Optional

REENTRY_WINDOW = 35


class ReentryClassifier:

    def __init__(self):
        self.active = False
        self.start_ts = 0.0
        self.prev_anchor = None

        self.first_hit_ts: Optional[float] = None
        self.visited = set()
        self.resets = 0
        self.events = 0

    def start(self, ts: float, previous_anchor: Optional[str]):
        self.active = True
        self.start_ts = ts
        self.prev_anchor = previous_anchor
        self.first_hit_ts = None
        self.visited.clear()
        self.resets = 0
        self.events = 0
        print("\n[REENTRY START]")

    def observe(self, ts: float, semantic: str, similar: bool, reset: bool):
        if not self.active:
            return None

        self.events += 1
        self.visited.add(semantic)

        if reset:
            self.resets += 1

        if similar and self.first_hit_ts is None:
            self.first_hit_ts = ts

        if ts - self.start_ts >= REENTRY_WINDOW:
            return self.finish(ts)

        return None

    def finish(self, ts: float):
        self.active = False

        latency = (self.first_hit_ts - self.start_ts) if self.first_hit_ts else 999

        entropy = len(self.visited)

        if latency < 2 and entropy <= 2:
            verdict = "CONTINUED"
        elif latency < 10:
            verdict = "RESUMED"
        elif latency < 35 and self.first_hit_ts:
            verdict = "RECONSTRUCTED"
        else:
            verdict = "REPLACED"

        print(f"[REENTRY RESULT] {verdict}\n")
        return verdict
