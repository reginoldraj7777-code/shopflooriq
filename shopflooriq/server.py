"""Loopback-only, dependency-free local demonstration HTTP server."""
import csv
import io
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .store import initialize, connect, command, DEFAULT_DB, ROOT, rows, payloads, audit, ingest, refresh, meta
from .generator import generate
from .analytics import snapshot, order_detail


def reset(db, actor, confirmation):
    from .store import authorize
    authorize(actor, {"admin"})
    if confirmation != "RESET":
        raise ValueError("Type RESET to restore the synthetic scenario")
    with db:
        db.execute("BEGIN IMMEDIATE")
        seed = meta(db, "seed")
        before = {"source_rows": db.execute("SELECT count(*) FROM raw_events").fetchone()[0]}
        for table in ("proposals", "incidents", "findings", "facts", "evidence", "checks", "raw_events", "orders", "products", "stations"):
            db.execute(f"DELETE FROM {table}")
        data = generate(seed)
        for table in ("products", "stations", "orders", "checks", "evidence"):
            db.executemany(f"INSERT INTO {table} VALUES(?,?)", [(x["id"], json.dumps(x)) for x in data[table]])
        ingest(db, data["events"])
        result = refresh(db)
        audit(db, actor, "scenario_reset", "scenario", before, result)
        return result


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, db_path=DEFAULT_DB):
        self.db_path = db_path
        self.csrf = secrets.token_urlsafe(32)
        db = initialize(db_path)
        db.close()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, data, status=200, content_type="application/json; charset=utf-8", filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.valid_host():
            return self.send({"error": "Loopback host required"}, 403)
        parsed = urlparse(self.path)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        db = connect(self.server.db_path)
        try:
            db.execute("BEGIN")  # One consistent read snapshot across facts, reviews and audit.
            if parsed.path == "/api/state":
                self.send(dict(snapshot(db, params), csrf=self.server.csrf))
            elif parsed.path == "/api/order":
                self.send(order_detail(db, params.get("id")))
            elif parsed.path == "/api/export":
                facts = [f for f in snapshot(db, params)["facts"] if f["trust"] == "trusted"]
                out = io.StringIO(newline="")
                writer = csv.DictWriter(out, fieldnames=["order_id", "day", "station", "shift", "product", "units", "elapsed", "wait", "late", "completed"], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(facts)
                self.send(out.getvalue().encode(), content_type="text/csv; charset=utf-8", filename="shopflooriq-synthetic-trusted.csv")
            elif parsed.path == "/api/source":
                self.send(json.dumps(payloads(db, "raw_events"), indent=2).encode(), filename="shopflooriq-synthetic-events.json")
            else:
                files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/experience.js": ("experience.js", "text/javascript"), "/styles.css": ("styles.css", "text/css"), "/favicon.svg": ("favicon.svg", "image/svg+xml")}
                if parsed.path not in files:
                    return self.send({"error": "Not found"}, 404)
                name, mime = files[parsed.path]
                self.send((ROOT / "web" / name).read_bytes(), content_type=mime + "; charset=utf-8")
        except ValueError as exc:
            self.send({"error": str(exc)}, 400)
        except Exception:
            import traceback
            traceback.print_exc()
            self.send({"error": "Unexpected server error. See the local console."}, 500)
        finally:
            db.close()

    def do_POST(self):
        origins = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        if not self.valid_host() or self.headers.get("Origin") not in origins or self.headers.get("X-CSRF-Token") != self.server.csrf:
            return self.send({"error": "Same-origin request and valid CSRF token required"}, 403)
        db = connect(self.server.db_path)
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length < 1 or length > 2_000_000:
                raise ValueError("Request body must be 1 byte to 2 MB")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object")
            action = self.path.removeprefix("/api/")
            actor = self.headers.get("X-Demo-Actor", "jules")
            result = reset(db, actor, body.get("confirmation")) if action == "reset" else command(db, actor, action, body)
            self.send(result)
        except PermissionError as exc:
            self.send({"error": str(exc)}, 403)
        except (ValueError, TypeError, KeyError) as exc:
            self.send({"error": str(exc)}, 400)
        except Exception:
            import traceback
            traceback.print_exc()
            self.send({"error": "Unexpected server error; changes rolled back. See the local console."}, 500)
        finally:
            db.close()


def serve(path=DEFAULT_DB, port=8765):
    server = Server(("127.0.0.1", port), path)
    print(f"ShopfloorIQ | Synthetic local demo | http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
