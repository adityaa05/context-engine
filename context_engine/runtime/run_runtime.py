import subprocess
import json
import re
from typing import Optional

from .loop_detector import LoopDetector, Event
from .event_bus import EventBus
from .events import CognitiveEvent, EventType
from .goal_continuity import GoalContinuity


# -------- HELPERS --------


def extract_app_from_anchor(anchor: str) -> str:
    """
    Anchors are like:
    'code loop_detector py context engine'
    'firefox stackoverflow flutter error'

    First token = app
    """
    parts = anchor.split()
    return parts[0] if parts else "unknown"


# -------- LOG SOURCE --------

LOG_CMD = [
    "log",
    "stream",
    "--style",
    "compact",
    "--predicate",
    'subsystem == "com.context.agent"',
]


# -------- JSON EXTRACTION --------

JSON_RE = re.compile(r"{.*?}")


def extract_json(line: str) -> Optional[dict]:
    match = JSON_RE.search(line)
    if not match:
        return None

    raw = match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


# -------- EPISODE CONTROLLER --------


class EpisodeController:

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.goal = GoalContinuity()
        self.current_episode: Optional[int] = None
        self.next_episode_id = 1
        self.current_anchor: Optional[str] = None

    def on_loop_start(self, event: CognitiveEvent):

        anchor = event.anchor or ""
        app = anchor.split()[0] if anchor else ""

        same_goal = self.goal.is_same_goal(app=app, anchor=anchor)

        if same_goal:
            return

        if self.current_episode is not None:
            self.bus.emit(
                CognitiveEvent(
                    ts=event.ts,
                    type=EventType.EPISODE_END,
                    anchor=self.current_anchor,
                    episode_id=self.current_episode,
                )
            )

        self.current_episode = self.next_episode_id
        self.next_episode_id += 1
        self.current_anchor = anchor

        self.bus.emit(
            CognitiveEvent(
                ts=event.ts,
                type=EventType.EPISODE_START,
                anchor=anchor,
                episode_id=self.current_episode,
            )
        )


# -------- DEBUG LISTENER --------


def debug_listener(event: CognitiveEvent):
    print(event)


# -------- MAIN RUNTIME --------


def main() -> None:

    bus = EventBus()

    detector = LoopDetector(bus)
    controller = EpisodeController(bus)

    # -------- EPISODE ROUTER --------
    def router(event: CognitiveEvent):

        # Always print cognition stream
        debug_listener(event)

        # Only LOOP_START affects episode boundaries
        if event.type == EventType.LOOP_START:

            if event.anchor is None:
                return

            controller.on_loop_start(
                ts=event.ts,
                app=extract_app_from_anchor(event.anchor),
                anchor=event.anchor,
            )

    bus.subscribe(router)

    proc = subprocess.Popen(
        LOG_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print("Context runtime connected to agent\n")

    try:
        assert proc.stdout is not None

        for line in proc.stdout:
            data = extract_json(line)
            if not data:
                continue

            try:
                event = Event(
                    ts=float(data["ts"]),
                    app=str(data.get("app", "")),
                    title=str(data.get("title", "")),
                    idle=float(data["idle"]),
                )

                detector.process(event)

            except (KeyError, ValueError, TypeError):
                continue

    except KeyboardInterrupt:
        print("\nStopping context runtime...")

    finally:
        proc.terminate()
        proc.wait(timeout=2)


# -------- ENTRYPOINT --------

if __name__ == "__main__":
    main()
