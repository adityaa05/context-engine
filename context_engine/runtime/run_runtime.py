import subprocess
import json
from session_builder import SessionBuilder, Event


LOG_CMD = [
    "log",
    "stream",
    "--style",
    "json",
    "--level",
    "debug",
    "--predicate",
    'subsystem == "com.context.agent"',
]


def stream_events(proc):
    buffer = ""
    depth = 0

    while True:
        ch = proc.stdout.read(1)
        if not ch:
            break

        if ch == "{":
            depth += 1

        if depth > 0:
            buffer += ch

        if ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    yield json.loads(buffer)
                except Exception:
                    pass
                buffer = ""


def main():
    builder = SessionBuilder()

    proc = subprocess.Popen(
        LOG_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print("Listening to ContextAgent...\n")

    for entry in stream_events(proc):
        msg = entry.get("eventMessage")

        if not msg or "|" not in msg:
            continue

        ts, app, title, idle = msg.split("|", 3)
        event = Event(float(ts), app, title, float(idle))
        builder.process(event)


if __name__ == "__main__":
    main()
