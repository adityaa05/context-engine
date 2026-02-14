from AppKit import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    kAXFocusedWindowAttribute,
    kAXTitleAttribute,
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt,
)

from Quartz import (
    CGEventSourceSecondsSinceLastEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType,
)

from context_engine.observer.base import BaseObserver


class MacOSAXObserver(BaseObserver):

    def __init__(self):
        # THIS triggers the macOS permission popup
        options = {kAXTrustedCheckOptionPrompt: True}
        trusted = AXIsProcessTrustedWithOptions(options)

        if not trusted:
            print("\n macOS is asking for Accessibility permission.")
            print("Approve it, then RE-RUN the program.\n")
            raise SystemExit(1)

    def get_idle_seconds(self) -> float:
        return CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateHIDSystemState,
            kCGAnyInputEventType,
        )

    def get_active_window(self) -> tuple[str, str]:
        active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        app_name = active_app.localizedName()
        pid = active_app.processIdentifier()

        app_ref = AXUIElementCreateApplication(pid)

        try:
            window = AXUIElementCopyAttributeValue(
                app_ref, kAXFocusedWindowAttribute, None
            )[0]
            title = AXUIElementCopyAttributeValue(window, kAXTitleAttribute, None)[0]
            return app_name, title if title else ""
        except Exception:
            return app_name, ""
