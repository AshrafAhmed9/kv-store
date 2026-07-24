"""TCP server: one thread per connected client, all sharing one KVStore.

Thread safety comes entirely from KVStore's own lock — this file just
translates protocol lines into store method calls.
"""
from __future__ import annotations
import logging
import signal
import socketserver
from kvstore.store import KVStore
from kvstore.wal import WAL
from kvstore.protocol import parse, ok, value, integer, error, multi_value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _dispatch(store: KVStore, cmd: str, args: list[str]) -> str:
    try:
        return _COMMANDS[cmd](store, args)
    except KeyError:
        return error(f"unknown command '{cmd}'")
    except Exception as e:
        log.warning("command error: %s", e)
        return error(str(e))


def _cmd_set(store: KVStore, args: list[str]) -> str:
    if len(args) < 2:
        return error("usage: SET key value [EX seconds]")
    ttl = float(args[3]) if len(args) == 4 and args[2].upper() == "EX" else None
    store.set(args[0], args[1], ttl=ttl)
    return ok()


def _cmd_get(store: KVStore, args: list[str]) -> str:
    if len(args) != 1:
        return error("usage: GET key")
    return value(store.get(args[0]))


def _cmd_delete(store: KVStore, args: list[str]) -> str:
    if len(args) != 1:
        return error("usage: DELETE key")
    return integer(int(store.delete(args[0])))


def _cmd_incr(store: KVStore, args: list[str]) -> str:
    if len(args) != 1:
        return error("usage: INCR key")
    return integer(store.incr(args[0]))


def _cmd_keys(store: KVStore, args: list[str]) -> str:
    return value(" ".join(store.keys()) or "(empty)")


def _cmd_scan(store: KVStore, args: list[str]) -> str:
    if len(args) != 2:
        return error("usage: SCAN start end")
    return multi_value(store.scan(args[0], args[1]))


_COMMANDS = {
    "SET": _cmd_set, "GET": _cmd_get, "DELETE": _cmd_delete,
    "INCR": _cmd_incr, "KEYS": _cmd_keys, "SCAN": _cmd_scan,
}


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        log.info("client connected: %s", self.client_address)
        try:
            for raw in self.rfile:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                self._handle_line(line)
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            log.info("client disconnected: %s", self.client_address)

    def _handle_line(self, line: str) -> None:
        try:
            cmd, args = parse(line)
        except ValueError as e:
            self.wfile.write(error(str(e)).encode())
            return
        self.wfile.write(_dispatch(self.server.store, cmd, args).encode())


class KVServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, store: KVStore, host: str = "127.0.0.1", port: int = 6379):
        self.store = store
        super().__init__((host, port), _Handler)


def main() -> None:
    from kvstore import config as cfg
    conf = cfg.load()

    wal = WAL(directory=conf.wal_path, sync_every=conf.sync_every)
    store = KVStore(wal=wal, sst_dir=conf.sst_dir,
                     memtable_size=conf.memtable_size,
                     compaction_trigger=conf.compaction_trigger)
    server = KVServer(store, host=conf.server_host, port=conf.server_port)

    def _handle_sigterm(signum, frame):
        log.info("SIGTERM received — shutting down...")
        server.shutdown()

    signal.signal(signal.SIGTERM, _handle_sigterm)

    log.info("KV store listening on %s:%s", conf.server_host, conf.server_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down gracefully...")
    finally:
        server.server_close()
        wal.close()
        log.info("shutdown complete.")


if __name__ == "__main__":
    main()
