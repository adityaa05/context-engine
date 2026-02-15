from collections import deque, Counter
from dataclasses import dataclass


# -------- EVENT --------


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


# -------- PARAMETERS --------

WINDOW = 45  # working memory window (seconds)
ANCHOR_THRESHOLD = 3  # returns needed to confirm a loop


# -------- LOOP DETECTOR --------


class LoopDetector:
    def __init__(self):
        # loop detection
        self.buffer = deque()
        self.anchor = None

        # cognition tracking
        self.prev_idle = None
        self.idle_resets = deque(maxlen=8)
        self.state = None

    # ---------------- PROCESS ----------------

    def process(self, e: Event):
        self.buffer.append(e)

        # remove old events outside working memory
        while self.buffer and (e.ts - self.buffer[0].ts) > WINDOW:
            self.buffer.popleft()

        self.update_state(e)
        self.detect_loop(e)

    # ---------------- STATE MODEL ----------------

    def update_state(self, e: Event):

        # first event
        if self.prev_idle is None:
            self.prev_idle = e.idle
            return

        # detect idle reset (user interaction burst)
        delta = self.prev_idle - e.idle
        self.prev_idle = e.idle

        reset = delta > 1.5 and e.idle < 0.3
        self.idle_resets.append(reset)

        resets = sum(self.idle_resets)
        samples = len(self.idle_resets)

        if samples < 5:
            return

        ratio = resets / samples

        # --- cognitive states ---
        if e.idle > 15:
            new_state = "AWAY"

        elif ratio > 0.45:
            new_state = "ENGAGED"  # typing / active thinking

        elif ratio > 0.15:
            new_state = "SCANNING"  # searching / switching

        else:
            new_state = "ABSORBED"  # watching / reading

        if new_state != self.state:
            self.state = new_state
            print(f"[STATE] {self.state}")

    # ---------------- LOOP MODEL ----------------

    def detect_loop(self, e: Event):

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
