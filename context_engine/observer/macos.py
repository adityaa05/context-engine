from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    CGEventSourceSecondsSinceLastEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType,
)

from context_engine.observer.base import BaseObserver


class MacOSObserver(BaseObserver):

    def get_idle_seconds(self) -> float:
        return CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateHIDSystemState,
            kCGAnyInputEventType,
        )

    def get_active_window(self) -> tuple[str, str]:
        windows = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly, kCGNullWindowID
        )

        for w in windows:
            if w.get("kCGWindowLayer") == 0:
                app = w.get("kCGWindowOwnerName", "Unknown")
                title = w.get("kCGWindowName", "") or ""
                return app, title

        return "Unknown", ""
