import time
from collections.abc import Callable

from .delivery import DeliveryResult, send
from .queue import EventQueue


def run_once(queue: EventQueue, *, max_attempts: int = 3, base_delay: float = 30,
             sender: Callable[[dict], DeliveryResult] = send,
             clock: Callable[[], float] = time.time) -> dict[str, int]:
    if max_attempts < 1 or base_delay <= 0:
        raise ValueError("Tentativas e intervalo precisam ser maiores que zero")
    counts = {"delivered": 0, "pending": 0, "failed": 0}
    for event in queue.ready(now=clock()):
        result = sender(event)
        if result.delivered:
            status = "delivered"
            next_attempt = 0
        else:
            attempts = event["attempts"] + 1
            retryable = result.status_code is None or result.status_code in {408, 429} or (
                result.status_code >= 500
            )
            status = "pending" if retryable and attempts < max_attempts else "failed"
            next_attempt = clock() + base_delay * 2 ** (attempts - 1) if status == "pending" else 0
        queue.record(event["id"], status, result.status_code, result.error, next_attempt)
        counts[status] += 1
    return counts
