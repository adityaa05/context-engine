from typing import Callable, List
from .events import CognitiveEvent


class EventBus:
    def __init__(self):
        self.subscribers: List[Callable[[CognitiveEvent], None]] = []

    def subscribe(self, fn: Callable[[CognitiveEvent], None]):
        self.subscribers.append(fn)

    def emit(self, event: CognitiveEvent):
        for s in self.subscribers:
            s(event)
