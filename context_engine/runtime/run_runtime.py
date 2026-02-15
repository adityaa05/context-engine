import subprocess
import json
from loop_detector import LoopDetector, Event

LOG_CMD = [
    "log",
    "stream",
    "--style",
    "compact",
    "--predicate",
    'subsystem == "com.context.agent"',
]


def extract_json(line: str):
    start = line.find("{")
    end = line.rfind("}")
    if start == -1 or end == -1:
        return None
    return line[start : end + 1]


def main():
    builder = LoopDetector()

    proc = subprocess.Popen(
        LOG_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print("Context runtime connected to agent\n")

    for raw in proc.stdout:
        raw = raw.strip()

        json_part = extract_json(raw)
        if not json_part:
            continue

        try:
            data = json.loads(json_part)

            event = Event(
                ts=float(data["ts"]),
                app=data["app"],
                title=data["title"],
                idle=float(data["idle"]),
            )

            builder.process(event)

        except Exception:
            # silent — logs contain garbage sometimes
            pass


if __name__ == "__main__":
    main()
