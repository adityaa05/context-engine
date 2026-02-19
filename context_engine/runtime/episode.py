from dataclasses import dataclass, field
from typing import List, Optional
from time import time


@dataclass
class Episode:

    id: int
    start_ts: float
    last_ts: float

    main_anchor: str
    anchors: List[str] = field(default_factory=list)

    loop_count: int = 0
    research_hops: int = 0
    suspend_count: int = 0

    broken: bool = False
    ended: bool = False

    def duration(self):
        return self.last_ts - self.start_ts
