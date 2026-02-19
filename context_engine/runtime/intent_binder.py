from typing import Optional
from .episode import Episode


EPISODE_TIMEOUT = 180  # 3 min no return = finished
RELATED_WINDOW = 90  # 90s counts as mental continuity


class IntentBinder:

    def __init__(self, bus):
        self.bus = bus
        self.current: Optional[Episode] = None
        self.counter = 0
        self.last_event_ts = 0
        self.last_reentry = None

    # ---------- INPUT EVENTS ----------

    def on_loop_start(self, ts: float, anchor: str):

        if self.current is None:
            self.start_episode(ts, anchor)
            return

        recent = (ts - self.current.last_ts) < RELATED_WINDOW
        related = self.related(anchor, self.current.main_anchor)
        resume = self.last_reentry == "RESUME"

        if recent and (related or resume):
            self.continue_episode(ts, anchor)
        else:
            self.end_episode(ts)
            self.start_episode(ts, anchor)

    def on_suspend(self, ts: float):
        if self.current:
            self.current.suspend_count += 1

    def on_reentry(self, ts: float, verdict: str):
        self.last_reentry = verdict

    # ---------- EPISODE OPS ----------

    def start_episode(self, ts: float, anchor: str):
        self.counter += 1
        self.current = Episode(self.counter, ts, ts, anchor)
        self.current.anchors.append(anchor)
        self.current.loop_count = 1
        self.bus.emit_episode_start(self.current)

    def continue_episode(self, ts: float, anchor: str):
        ep = self.current
        ep.last_ts = ts
        ep.loop_count += 1

        if anchor != ep.anchors[-1]:
            ep.research_hops += 1
            ep.anchors.append(anchor)

    def end_episode(self, ts: float):
        if not self.current:
            return

        self.current.last_ts = ts
        self.current.ended = True
        self.bus.emit_episode_end(self.current)
        self.current = None

    # ---------- RELATION ----------

    def related(self, a: str, b: str) -> bool:

        ta = set(a.split())
        tb = set(b.split())

        if not ta or not tb:
            return False

        overlap = len(ta & tb) / max(len(ta), len(tb))

        return overlap > 0.35
