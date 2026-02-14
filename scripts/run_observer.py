import time
import platform

from context_engine.observer.macos_ax import MacOSAXObserver


def get_observer():
    if platform.system() == "Darwin":
        return MacOSAXObserver()
    raise NotImplementedError("OS not supported yet")


def main():
    observer = get_observer()

    print("Recording events... Ctrl+C to stop\n")

    try:
        while True:
            event = observer.poll()
            print(
                f"{event.timestamp.strftime('%H:%M:%S')} | "
                f"{event.app:20} | "
                f"{str(event.title or '')[:40]:40} | "
                f"idle={event.idle_seconds:.1f}"
            )
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
