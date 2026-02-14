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


def iter_log_objects(proc):
    buffer = ""
    for line in proc.stdout:
        line = line.strip()

        if not line:
            continue

        # remove array brackets safely
        if line in ("[", "]", ","):
            continue

        # remove trailing comma
        if line.endswith(","):
            line = line[:-1]

        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


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

    for entry in iter_log_objects(proc):
        msg = entry.get("eventMessage")
        if not msg or "|" not in msg:
            continue

        try:
            ts, app, title, idle = msg.rsplit("|", 3)
            event = Event(float(ts), app, title, float(idle))
            builder.process(event)
        except Exception:
            pass


if __name__ == "__main__":
    main()
