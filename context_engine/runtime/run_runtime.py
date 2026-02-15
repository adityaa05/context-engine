import subprocess
import json

from loop_detector import LoopDetector, Event
from cognitive_state import CognitiveState

LOG_CMD = [
    "log",
    "stream",
    "--style",
    "compact",
    "--predicate",
    'subsystem == "com.context.agent"',
]


def extract_json(line):
    start = line.find("{")
    end = line.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(line[start : end + 1])
    except:
        return None


def main():
    loops = LoopDetector()
    brain = CognitiveState()

    proc = subprocess.Popen(
        LOG_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print("Context runtime connected to agent\n")

    for line in proc.stdout:
        data = extract_json(line)
        if not data:
            continue

        event = Event(
            ts=float(data["ts"]),
            app=data["app"],
            title=data["title"],
            idle=float(data["idle"]),
        )

        loops.process(event)
        brain.process(event)


if __name__ == "__main__":
    main()
