import subprocess
import re
from session_builder import SessionBuilder, Event

LOG_CMD = [
    "log",
    "stream",
    "--style",
    "compact",
    "--predicate",
    'subsystem == "com.context.agent"',
]

pattern = re.compile(r".*sensor\] ([0-9.]+)\|(.+?)\|(.+?)\|([0-9.]+)")


def parse_line(line):
    m = pattern.match(line)
    if not m:
        return None

    ts = float(m.group(1))
    app = m.group(2).strip()
    title = m.group(3).strip()
    idle = float(m.group(4))

    return Event(ts, app, title, idle)


def main():
    builder = SessionBuilder()

    proc = subprocess.Popen(
        LOG_CMD, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1
    )

    print("Listening to ContextAgent...\n")

    for line in proc.stdout:
        event = parse_line(line)
        if event:
            builder.process(event)


if __name__ == "__main__":
    main()
