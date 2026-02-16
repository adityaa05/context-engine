from collections import deque
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Deque, Optional, Tuple, Set
import re
import json
import os
from pathlib import Path


# ---------------- NORMALIZATION ----------------

NOISE_PATTERNS = [
    r" — \d+×\d+",
    r" - YouTube",
    r"\(\d+\)",
    r"YouTube Video Player",
    r"YouTube Home",
]


def normalize(app: str, title: str) -> str:
    text = f"{app} {title}".lower()

    for p in NOISE_PATTERNS:
        text = re.sub(p, "", text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------- EVENT ----------------


@dataclass
class Event:
    ts: float
    app: str
    title: str
    idle: float


# ---------------- SEGMENT ----------------


@dataclass
class ThoughtSegment:
    start: float
    end: float
    anchor: str
    apps: Set[str]


# ---------------- STORAGE ----------------

MEMORY_DIR = Path.home() / ".context"
MEMORY_FILE = MEMORY_DIR / "memory.jsonl"


def persist_segment(segment: ThoughtSegment):
    MEMORY_DIR.mkdir(exist_ok=True)

    with open(MEMORY_FILE, "a") as f:
        json.dump(
            {
                "start": segment.start,
                "end": segment.end,
                "anchor": segment.anchor,
                "apps": list(segment.apps),
            },
            f,
        )
        f.write("\n")


# ---------------- PARAMETERS ----------------

WINDOW = 60
SIM_THRESHOLD = 0.72
ANCHOR_CONFIRM = 4


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ---------------- LOOP DETECTOR ----------------


class LoopDetector:

    def __init__(self) -> None:

        # working memory
        self.memory: Deque[Tuple[float, str]] = deque()

        # attractor
        self.anchor_text: Optional[str] = None
        self.anchor_hits: float = 0

        # active segment
        self.segment_start: Optional[float] = None
        self.segment_apps: Set[str] = set()

        # cognition tracking
        self.prev_idle: Optional[float] = None
        self.idle_resets: Deque[bool] = deque(maxlen=8)
        self.state: Optional[str] = None

    # ---------------- PROCESS ----------------

    def process(self, e: Event) -> None:
        self.update_state(e)
        self.detect_loop(e)

    # ---------------- STATE MODEL ----------------

    def update_state(self, e: Event) -> None:

        if self.prev_idle is None:
            self.prev_idle = e.idle
            return

        delta = self.prev_idle - e.idle
        self.prev_idle = e.idle

        reset = delta > 1.5 and e.idle < 0.3
        self.idle_resets.append(reset)

        if len(self.idle_resets) < 5:
            return

        ratio = sum(self.idle_resets) / len(self.idle_resets)

        if e.idle > 15:
            new_state = "AWAY"
        elif ratio > 0.45:
            new_state = "EXECUTING"
        elif ratio > 0.15:
            new_state = "SCANNING"
        else:
            new_state = "ABSORBED"

        if new_state != self.state:
            self.state = new_state
            print(f"[STATE] {self.state}")

    # ---------------- LOOP MODEL ----------------

    def detect_loop(self, e: Event) -> None:

        text = normalize(e.app, e.title)
        if not text:
            return

        # update segment apps
        if self.anchor_text:
            self.segment_apps.add(e.app)

        # update memory
        self.memory.append((e.ts, text))
        while self.memory and (e.ts - self.memory[0][0]) > WINDOW:
            self.memory.popleft()

        # find recurrence
        best_score = 0.0
        best_text: Optional[str] = None

        for _, past in self.memory:
            if past == text:
                continue

            s = similarity(text, past)
            if s > best_score:
                best_score = s
                best_text = past

        # recurrence
        if best_score > SIM_THRESHOLD:
            self.anchor_hits += 1
        elif len(self.memory) > 5:
            self.anchor_hits *= 0.85

        # ---------- LOOP START ----------
        if (
            self.anchor_hits >= ANCHOR_CONFIRM
            and best_text
            and self.anchor_text != best_text
        ):
            self.anchor_text = best_text
            self.segment_start = e.ts
            self.segment_apps = {e.app}

            print(f"\n[LOOP START] {best_text}")

        # ---------- LOOP END ----------
        if self.anchor_text and self.anchor_hits < 0.5:
            self.close_segment(e.ts)

    # ---------------- SEGMENT CLOSE ----------------

    def close_segment(self, end_ts: float):

        if not self.segment_start:
            self.anchor_text = None
            return

        segment = ThoughtSegment(
            start=self.segment_start,
            end=end_ts,
            anchor=self.anchor_text,
            apps=self.segment_apps,
        )

        persist_segment(segment)

        print(f"[LOOP END] {self.anchor_text}")

        self.anchor_text = None
        self.segment_start = None
        self.segment_apps = set()
        self.anchor_hits = 0
