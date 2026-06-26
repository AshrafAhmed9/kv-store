from __future__ import annotations
import json
import logging
import signal
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from core.metrics import Metrics
from core.store import KVStore
from core.wal import WAL
from .protocol import parse, ok, value, integer, error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _dispatch(store: KVStore, cmd: str, args: list[str], metrics: Metrics) -> str:
    try:
        if cmd == "SET":
            if len(args) < 2:
                return error("usage: SET key value [EX seconds]")
            ttl = float(args[3]) if len(args) == 4 and args[2].upper() == "EX" else None
            store.set(args[0], args[1], ttl=ttl)
            metrics.record_write()
            return ok()
        if cmd == "GET":
            if len(args) != 1:
                return error("usage: GET key")
            metrics.record_read()
            return value(store.get(args[0]))
        if cmd == "DELETE":
            if len(args) != 1:
                return error("usage: DELETE key")
            metrics.record_write()
            return integer(int(store.delete(args[0])))
        if cmd == "INCR":
            if len(args) != 1:
                return error("usage: INCR key")
            metrics.record_write()
            return integer(store.incr(args[0]))
        if cmd == "KEYS":
            metrics.record_read()
            return value(" ".join(store.keys()) or "(empty)")
        if cmd == "SCAN":
            if len(args) != 2:
                return error("usage: SCAN start end")
            metrics.record_read()
            from .protocol import multi_value
            return multi_value(store.scan(args[0], args[1]))

        return error(f"unknown command '{cmd}'")
    except Exception as e:
        log.warning("command error: %s", e)
        return error(str(e))


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        log.info("client connected: %s", self.client_address)
        try:
            for raw in self.rfile:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    cmd, args = parse(line)
                except ValueError as e:
                    self.wfile.write(error(str(e)).encode())
                    continue
                self.wfile.write(
                    _dispatch(self.server.store, cmd, args, self.server.metrics).encode()
                )
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            log.info("client disconnected: %s", self.client_address)


class KVServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, store: KVStore, metrics: Metrics,
                 host: str = "127.0.0.1", port: int = 6379):
        self.store   = store
        self.metrics = metrics
        super().__init__((host, port), _Handler)


def _start_metrics_server(metrics: Metrics, store: KVStore, host: str, port: int) -> None:
    def make_handler():
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/metrics":
                    data = json.dumps(
                        metrics.snapshot(len(store.keys())), indent=2
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass
        return Handler

    http = HTTPServer((host, port), make_handler())
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    log.info("metrics available at http://%s:%s/metrics", host, port)


if __name__ == "__main__":
    import config as cfg
    conf = cfg.load()

    wal = WAL(directory=conf.wal_path, sync_every=conf.sync_every)
    store   = KVStore(wal=wal)
    metrics = Metrics()
    server  = KVServer(store, metrics, host=conf.server_host, port=conf.server_port)

    def _handle_sigterm(signum, frame):
        log.info("SIGTERM received — shutting down...")
        server.shutdown()

    signal.signal(signal.SIGTERM, _handle_sigterm)
    _start_metrics_server(metrics, store, conf.server_host, conf.metrics_port)

    log.info("KV store listening on %s:%s", conf.server_host, conf.server_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down gracefully...")
    finally:
        server.server_close()
        wal.close()
        log.info("shutdown complete.")
