from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


@dataclass
class Session:
    start: float
    end: float
    app: str
    title: str


class Sessionizer:
    SWITCH_GAP = 8  # seconds of different context
    IDLE_BREAK = 20  # idle means break

    def __init__(self):
        self.current: Optional[Event] = None
        self.start_ts: Optional[float] = None

    def feed(self, event: Event):
        if self.current is None:
            self.current = event
            self.start_ts = event.ts
            return None

        # break on idle
        if event.idle > self.IDLE_BREAK:
            session = Session(
                self.start_ts, event.ts, self.current.app, self.current.title
            )
            self.current = None
            return session

        # context change
        if event.app != self.current.app or event.title != self.current.title:
            if event.ts - self.current.ts > self.SWITCH_GAP:
                session = Session(
                    self.start_ts, self.current.ts, self.current.app, self.current.title
                )
                self.start_ts = event.ts
                self.current = event
                return session

        self.current = event
        return None
