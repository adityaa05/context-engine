from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WindowEvent:
    timestamp: datetime
    app: str
    title: str
    is_idle: bool
    idle_seconds: float

