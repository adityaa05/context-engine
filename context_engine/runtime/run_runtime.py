import subprocess
import json
import re
from typing import Optional

from .loop_detector import LoopDetector, Event


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

JSON_RE = re.compile(r"\{.*?\}")


def extract_json(line: str) -> Optional[dict]:
    """
    macOS unified logs prepend metadata before the JSON.
    We safely extract the first JSON object in the line.
    """

    match = JSON_RE.search(line)
    if not match:
        return None

    raw = match.group(0)  # <-- not group(1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


# -------- MAIN RUNTIME --------


def main() -> None:
    detector = LoopDetector()

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
                    app=str(data["app"]),
                    title=str(data["title"]),
                    idle=float(data["idle"]),
                )

                detector.process(event)

            except (KeyError, ValueError, TypeError):
                # corrupted / partial log frame
                continue

    except KeyboardInterrupt:
        print("\nStopping context runtime...")

    finally:
        proc.terminate()
        proc.wait(timeout=2)


# -------- ENTRYPOINT --------

if __name__ == "__main__":
    main()
