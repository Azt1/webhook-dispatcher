import argparse
import json
import sqlite3
from pathlib import Path

from .queue import EventQueue
from .worker import run_once


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Use um número maior que zero")
    return number


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fila local para entrega de webhooks")
    parser.add_argument("--db", default="data/events.db", help="Arquivo SQLite da fila")
    commands = parser.add_subparsers(dest="command", required=True)
    enqueue = commands.add_parser("enqueue", help="Adiciona um evento à fila")
    enqueue.add_argument("url", help="Destino HTTP ou HTTPS")
    enqueue.add_argument("payload", type=Path, help="Arquivo com um objeto JSON")
    history = commands.add_parser("list", help="Mostra os estados dos eventos, sem exibir dados privados")
    history.add_argument("--status", choices=("pending", "delivered", "failed"),
                         help="Mostra apenas os eventos com esse estado")
    run = commands.add_parser("run", help="Processa um lote de até 100 eventos pendentes")
    run.add_argument("--attempts", type=positive_int, default=3)
    run.add_argument("--delay", type=positive_int, default=30, help="Intervalo inicial em segundos")
    args = parser.parse_args(argv)
    try:
        queue = EventQueue(args.db)
        if args.command == "enqueue":
            payload = json.loads(args.payload.read_text(encoding="utf-8-sig"))
            print(queue.add(args.url, payload))
        elif args.command == "list":
            rows = [{key: event[key] for key in ("id", "status", "attempts", "http_status", "last_error")}
                    for event in queue.list(status=args.status)]
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            counts = run_once(queue, max_attempts=args.attempts, base_delay=args.delay)
            print(json.dumps(counts))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
