from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True)
class DeliveryResult:
    status_code: int | None
    error: str | None = None

    @property
    def delivered(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 300


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send(event: dict, timeout: float = 10) -> DeliveryResult:
    if timeout <= 0:
        raise ValueError("O tempo limite precisa ser maior que zero")
    request = Request(
        event["url"],
        data=event["payload"].encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "webhook-dispatcher/0.1",
            "Idempotency-Key": event["id"],
        },
        method="POST",
    )
    try:
        with build_opener(NoRedirects()).open(request, timeout=timeout) as response:
            code = response.status
            return DeliveryResult(code, None if 200 <= code < 300 else f"HTTP {code}")
    except HTTPError as exc:
        code = exc.code
        exc.close()
        return DeliveryResult(code, f"HTTP {code}")
    except (URLError, TimeoutError, OSError) as exc:
        return DeliveryResult(None, f"Falha de conexão: {type(exc).__name__}")
