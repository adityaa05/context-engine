from .intent_binder import IntentBinder
from .events import EventType, CognitiveEvent


class IntentListener:

    def __init__(self, bus):
        self.binder = IntentBinder(bus)

    def __call__(self, event: CognitiveEvent):

        if event.type == EventType.LOOP_START:
            self.binder.on_loop_start(event.ts, event.anchor)

        elif event.type == EventType.SUSPEND:
            self.binder.on_suspend(event.ts)

        elif event.type == EventType.REENTRY:
            self.binder.on_reentry(event.ts, event.verdict)
