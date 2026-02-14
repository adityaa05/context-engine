import subprocess
from pathlib import Path


AGENT_PATH = (
    Path.home()
    / "Desktop/Projects/context-agent/ContextAgent.app/Contents/MacOS/ContextAgent"
)


def stream_events():
    proc = subprocess.Popen(
        [str(AGENT_PATH)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    for line in proc.stdout:
        yield line.strip()
