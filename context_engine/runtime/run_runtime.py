import subprocess
import json
import re
from loop_detector import LoopDetector, Event


LOG_CMD = [
    "log",
    "stream",
    "--style",
    "compact",
    "--predicate",
    'subsystem == "com.context.agent"',
]

# finds JSON inside macOS log line
json_pattern = re.compile(r"({.*})")


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

    for line in proc.stdout:
        match = json_pattern.search(line)
        if not match:
            continue

        try:
            data = json.loads(match.group(1))

            event = Event(
                ts=float(data["ts"]),
                app=data["app"],
                title=data["title"],
                idle=float(data["idle"]),
            )

            builder.process(event)

        except Exception:
            print("parse error:", line)


if __name__ == "__main__":
    main()
