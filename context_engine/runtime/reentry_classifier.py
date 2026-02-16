from typing import Optional

# observation window (hard cap)
MAX_OBSERVE = 15.0

# decision thresholds
FAST_SWITCH_TIME = 3.0
ABANDON_IDLE = 12.0
FAST_RESET = 2.0
RECONSTRUCT_MIN = 3.0


class ReentryClassifier:

    def __init__(self):
        self.active = False
        self.start_ts = 0.0
        self.prev_anchor: Optional[str] = None

        # observation metrics
        self.first_reset_ts: Optional[float] = None
        self.first_switch_ts: Optional[float] = None

        self.reset_count = 0
        self.last_semantic: Optional[str] = None
        self.max_idle = 0.0

    # ---------------- START ----------------

    def start(self, ts: float, previous_anchor: Optional[str]):
        self.active = True
        self.start_ts = ts
        self.prev_anchor = previous_anchor

        self.first_reset_ts = None
        self.first_switch_ts = None
        self.reset_count = 0
        self.last_semantic = None
        self.max_idle = 0.0

        print("\n[REENTRY START]")

    # ---------------- OBSERVE ----------------

    def observe(
        self, ts: float, semantic: str, similar: bool, reset: bool, idle: float
    ):
        if not self.active:
            return None

        elapsed = ts - self.start_ts
        self.max_idle = max(self.max_idle, idle)

        # detect app/task switch
        if self.last_semantic and semantic != self.last_semantic:
            if self.first_switch_ts is None:
                self.first_switch_ts = elapsed

        self.last_semantic = semantic

        # detect action
        if reset:
            self.reset_count += 1
            if self.first_reset_ts is None:
                self.first_reset_ts = elapsed

        # ---------- EARLY EXIT RULES ----------

        # immediate replacement
        if self.first_switch_ts is not None and self.first_switch_ts < FAST_SWITCH_TIME:
            return self.finish("REPLACED")

        # abandonment
        if self.max_idle > ABANDON_IDLE:
            return self.finish("ABANDONED")

        # decisive continuation
        if (
            self.first_reset_ts is not None
            and self.first_reset_ts < FAST_RESET
            and self.reset_count >= 3
        ):
            return self.finish("CONTINUED")

        # reconstruction pattern
        if (
            self.first_reset_ts is not None
            and RECONSTRUCT_MIN <= self.first_reset_ts <= 10
            and self.reset_count >= 2
        ):
            return self.finish("RECONSTRUCTED")

        # hard timeout
        if elapsed >= MAX_OBSERVE:
            return self.finish(self.default_verdict())

        return None

    # ---------------- DEFAULT DECISION ----------------

    def default_verdict(self):
        if self.reset_count == 0:
            return "ABANDONED"
        if self.first_reset_ts and self.first_reset_ts < 4:
            return "CONTINUED"
        return "REPLACED"

    # ---------------- FINISH ----------------

    def finish(self, verdict: str):
        self.active = False
        print(f"[REENTRY RESULT] {verdict}\n")
        return verdict
