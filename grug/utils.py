import signal
import time
from contextlib import contextmanager
from functools import wraps

from loguru import logger


class TimeoutException(Exception):
    pass


def log_runtime(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        runtime = end_time - start_time
        logger.info(f"Function {func.__name__} ran for {runtime:.4f} seconds")
        return result

    return wrapper


@contextmanager
def timeout(seconds: int):
    def _handle_timeout(signum, frame):
        raise TimeoutException(f"Function call timed out after {seconds} seconds")

    signal.signal(signal.SIGALRM, _handle_timeout)  # type: ignore
    signal.alarm(seconds)  # type: ignore
    try:
        yield
    finally:
        signal.alarm(0)  # type: ignore
