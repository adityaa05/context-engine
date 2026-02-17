from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EventType(str, Enum):

    # Loop lifecycle
    LOOP_START = "LOOP_START"
    LOOP_END = "LOOP_END"

    # Cognitive state
    PHASE = "PHASE"

    # Attention breaks
    SUSPEND = "SUSPEND"
    REENTRY = "REENTRY"


@dataclass
class CognitiveEvent:
    ts: float
    type: EventType

    # optional payloads
    anchor: Optional[str] = None
    phase: Optional[str] = None
    verdict: Optional[str] = None
