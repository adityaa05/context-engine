from typing import Callable, List
from .events import CognitiveEvent, EventType


class EventBus:
    """
    Central cognitive event stream.
    LoopDetector emits structured cognition signals here.
    Runtime / UI / DB subscribe to it.
    """

    def __init__(self):
        self.listeners: List[Callable[[CognitiveEvent], None]] = []

    # ---------------- SUBSCRIBE ----------------

    def subscribe(self, fn: Callable[[CognitiveEvent], None]):
        self.listeners.append(fn)

    # ---------------- CORE EMIT ----------------

    def _emit(self, event: CognitiveEvent):
        for fn in self.listeners:
            fn(event)

    # ---------------- SEMANTIC EVENTS ----------------

    def emit_loop_start(self, ts: float, anchor: str):
        self._emit(CognitiveEvent(ts=ts, type=EventType.LOOP_START, anchor=anchor))

    def emit_loop_end(self, ts: float):
        self._emit(CognitiveEvent(ts=ts, type=EventType.LOOP_END))

    def emit_phase(self, ts: float, phase: str):
        self._emit(CognitiveEvent(ts=ts, type=EventType.PHASE, phase=phase))

    def emit_suspend(self, ts: float):
        self._emit(CognitiveEvent(ts=ts, type=EventType.SUSPEND))

    def emit_reentry(self, ts: float, verdict: str):
        self._emit(CognitiveEvent(ts=ts, type=EventType.REENTRY, verdict=verdict))
