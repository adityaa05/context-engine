from context_engine.runtime.stream import stream_events
from context_engine.runtime.sessionizer import Event, Sessionizer

s = Sessionizer()

for raw in stream_events():
    ts, app, title, idle = raw.split("|")
    event = Event(float(ts), app, title, float(idle))

    session = s.feed(event)
    if session:
        print(
            f"[{session.start:.0f}-{session.end:.0f}] "
            f"{session.app} :: {session.title}"
        )
