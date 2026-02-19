from typing import Callable, List
from .events import CognitiveEvent, EventType


class EventBus:

    def __init__(self):
        self.listeners: List[Callable[[CognitiveEvent], None]] = []

    def subscribe(self, fn: Callable[[CognitiveEvent], None]):
        self.listeners.append(fn)

    def emit(self, event: CognitiveEvent):
        for l in self.listeners:
            l(event)

    # -------- cognitive --------

    def emit_loop_start(self, ts, anchor):
        self.emit(CognitiveEvent(ts, EventType.LOOP_START, anchor=anchor))

    def emit_phase(self, ts, phase):
        self.emit(CognitiveEvent(ts, EventType.PHASE, phase=phase))

    def emit_suspend(self, ts):
        self.emit(CognitiveEvent(ts, EventType.SUSPEND))

    def emit_reentry(self, ts, verdict):
        self.emit(CognitiveEvent(ts, EventType.REENTRY, verdict=verdict))

    # -------- episodes --------

    def emit_episode_start(self, ep):
        self.emit(
            CognitiveEvent(
                ts=ep.start_ts,
                type=EventType.EPISODE_START,
                anchor=ep.main_anchor,
                episode_id=ep.id,
            )
        )

    def emit_episode_end(self, ep):
        self.emit(
            CognitiveEvent(
                ts=ep.last_ts,
                type=EventType.EPISODE_END,
                anchor=ep.main_anchor,
                episode_id=ep.id,
            )
        )
