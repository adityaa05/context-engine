from abc import ABC, abstractmethod
from context_engine.state.event import WindowEvent


class BaseObserver(ABC):
    """Platform-independent observer interface"""

    @abstractmethod
    def get_active_window(self) -> tuple[str, str]:
        """Returns (app_name, window_title)"""
        pass

    @abstractmethod
    def get_idle_seconds(self) -> float:
        """Seconds since last user input"""
        pass

    def poll(self) -> WindowEvent:
        """Unified event builder"""
        from datetime import datetime

        app, title = self.get_active_window()
        idle = self.get_idle_seconds()

        return WindowEvent(
            timestamp=datetime.now(),
            app=app,
            title=title,
            is_idle=idle > 120,  # temporary heuristic
            idle_seconds=idle,
        )
