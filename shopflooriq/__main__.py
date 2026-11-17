import argparse
import json
from .store import DEFAULT_DB, initialize, command
from .server import serve, reset
from .analytics import snapshot


def main():
    parser = argparse.ArgumentParser(description="ShopfloorIQ · independent synthetic demonstration")
    parser.add_argument("action", choices=["serve", "generate", "validate", "reset", "evaluate", "ingest"], nargs="?", default="serve")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed", type=int, default=1042)
    parser.add_argument("--file", help="JSON array of source events to stage")
    args = parser.parse_args()
    if args.action == "serve":
        serve(args.db, args.port)
        return
    db = initialize(args.db, args.seed)
    try:
        if args.action == "reset":
            print(json.dumps(reset(db, "robin", "RESET"), indent=2))
        elif args.action == "validate":
            print(json.dumps(command(db, "robin", "refresh", {}), indent=2))
        elif args.action == "evaluate":
            lab = snapshot(db)["lab"]
            print(json.dumps({k:v for k,v in lab.items() if k != "signals"}, indent=2))
        elif args.action == "ingest":
            if not args.file:
                parser.error("ingest requires --file")
            with open(args.file, encoding="utf-8") as f:
                print(json.dumps(command(db, "robin", "ingest", {"events": json.load(f)}), indent=2))
        else:
            print(json.dumps(snapshot(db)["metrics"], indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
