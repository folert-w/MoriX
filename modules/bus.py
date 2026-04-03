from typing import Callable, Dict, List, Any
from threading import RLock

class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}
        self._lock = RLock()

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        with self._lock:
            self._subscribers.setdefault(event, []).append(callback)

    def emit(self, event: str, *args, **kwargs) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception:
                pass

bus = EventBus()
