from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EventType(str, Enum):
    LOOP_START = "LOOP_START"
    PHASE = "PHASE"
    SUSPEND = "SUSPEND"
    REENTRY = "REENTRY"

    # NEW
    EPISODE_START = "EPISODE_START"
    EPISODE_END = "EPISODE_END"


@dataclass
class CognitiveEvent:
    ts: float
    type: EventType
    anchor: Optional[str] = None
    phase: Optional[str] = None
    verdict: Optional[str] = None
    episode_id: Optional[int] = None
