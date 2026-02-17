from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------------- EVENT TYPES ----------------

class EventType(str, Enum):
    LOOP_START = "LOOP_START"
    LOOP_END = "LOOP_END"

    PHASE = "PHASE"

    SUSPEND = "SUSPEND"

    REENTRY_START = "REENTRY_START"
    REENTRY_RESULT = "REENTRY_RESULT"


# ---------------- EVENT STRUCT ----------------

@dataclass
class CognitiveEvent:
    ts: float
    type: EventType

    # optional payloads
    anchor: Optional[str] = None
    phase: Optional[str] = None
    verdict: Optional[str] = None
