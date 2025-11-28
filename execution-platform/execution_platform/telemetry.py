from contextlib import contextmanager
from typing import Optional

@contextmanager
def span(name: str, enabled: bool = False, **attrs):
    if not enabled:
        yield None
        return
    try:
        yield None
    finally:
        pass

def record_event(enabled: bool, **attrs):
    return None
