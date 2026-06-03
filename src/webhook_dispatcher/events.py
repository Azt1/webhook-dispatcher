import json
from urllib.parse import urlsplit


def validate_event(url: str, payload: dict) -> str:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise ValueError("Endereço de webhook inválido") from exc
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("O webhook precisa de um endereço HTTP ou HTTPS")
    if parts.username is not None or parts.password is not None or parts.fragment:
        raise ValueError("Não coloque credenciais ou fragmentos no endereço")
    if port == 0:
        raise ValueError("Porta inválida")
    if not isinstance(payload, dict):
        raise ValueError("O evento precisa ser um objeto JSON")
    try:
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("O evento contém dados que não podem ser enviados como JSON") from exc
