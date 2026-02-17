from typing import Optional

EARLY_DECISION_THRESHOLD = 4
MAX_WINDOW = 40


class ReentryClassifier:

    def __init__(self):
        self.active = False
        self.start_ts = 0.0
        self.prev_anchor = None

        self.first_similar_ts: Optional[float] = None
        self.last_ts: float = 0.0

        self.visited = set()
        self.resets = 0
        self.events = 0

        # confidence scores
        self.score_continued = 0
        self.score_resumed = 0
        self.score_reconstructed = 0
        self.score_replaced = 0

    # ---------------- START ----------------

    def start(self, ts: float, previous_anchor: Optional[str]):
        self.active = True
        self.start_ts = ts
        self.prev_anchor = previous_anchor
        self.first_similar_ts = None
        self.last_ts = ts

        self.visited.clear()
        self.resets = 0
        self.events = 0

        self.score_continued = 0
        self.score_resumed = 0
        self.score_reconstructed = 0
        self.score_replaced = 0

        print("\n[REENTRY START]")

    # ---------------- OBSERVE ----------------

    def observe(self, ts: float, semantic: str, similar: bool, reset: bool):

        if not self.active:
            return None

        self.events += 1
        self.visited.add(semantic)

        if reset:
            self.resets += 1

        latency = ts - self.start_ts

        if similar and self.first_similar_ts is None:
            self.first_similar_ts = ts

        # -------- Evidence accumulation --------

        if similar and latency < 1.5:
            self.score_continued += 3

        elif similar and latency < 8:
            self.score_reconstructed += 2

        elif similar:
            self.score_resumed += 2

        if len(self.visited) >= 4:
            self.score_resumed += 2

        if self.resets >= 3:
            self.score_resumed += 2

        if not similar and latency > 6:
            self.score_replaced += 3

        # -------- Early decision --------
        verdict = self.try_finish(ts)
        if verdict:
            return verdict

        # -------- Fallback timeout --------
        if ts - self.start_ts > MAX_WINDOW:
            return self.force_finish(ts)

        return None

    # ---------------- DECISION ----------------

    def try_finish(self, ts):

        scores = {
            "CONTINUED": self.score_continued,
            "RECONSTRUCTED": self.score_reconstructed,
            "RESUMED": self.score_resumed,
            "REPLACED": self.score_replaced,
        }

        best = max(scores, key=scores.get)

        if scores[best] >= EARLY_DECISION_THRESHOLD:
            return self.finish(best)

        return None

    def force_finish(self, ts):

        scores = {
            "CONTINUED": self.score_continued,
            "RECONSTRUCTED": self.score_reconstructed,
            "RESUMED": self.score_resumed,
            "REPLACED": self.score_replaced,
        }

        best = max(scores, key=scores.get)
        return self.finish(best)

    # ---------------- END ----------------

    def finish(self, verdict):
        self.active = False
        print(f"[REENTRY RESULT] {verdict}\n")
        return verdict
