from AppKit import NSWorkspace

# Import ALL Accessibility APIs from ApplicationServices
try:
    from ApplicationServices import (
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        kAXFocusedWindowAttribute,
        kAXTitleAttribute,
    )
except ImportError:
    # Ultimate fallback (very unlikely to work with modern PyObjC)
    from Quartz import (
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        kAXFocusedWindowAttribute,
        kAXTitleAttribute,
    )

# Keep ONLY Core Graphics APIs in Quartz
from Quartz import (
    CGEventSourceSecondsSinceLastEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType,
)

from context_engine.observer.base import BaseObserver


class MacOSAXObserver(BaseObserver):
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
            window_ref, _ = AXUIElementCopyAttributeValue(
                app_ref, kAXFocusedWindowAttribute, None
            )
            title, _ = AXUIElementCopyAttributeValue(
                window_ref, kAXTitleAttribute, None
            )
            return app_name, str(title) if title else ""
        except Exception:
            return app_name, ""
