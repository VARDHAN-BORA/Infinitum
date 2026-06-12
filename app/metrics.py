import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Timer:
    """Holds the measured duration after a `track()` block completes."""
    elapsed_ms: float = field(default=0.0)


@contextmanager
def track(timer: Timer):
    """
    Measure wall-clock duration of a code block in milliseconds.

    Works with both sync and async code — `await` inside the block is fine
    because perf_counter captures the real elapsed time including I/O waits,
    which is exactly the latency the caller experiences.

    Usage:
        t = Timer()
        with track(t):
            result = await some_async_call()
        print(t.elapsed_ms)   # e.g. 312.5
    """
    start = time.perf_counter()
    try:
        yield timer
    finally:
        timer.elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
