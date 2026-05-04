from __future__ import annotations
import socketserver
import config
from core.store import KVStore
from core.wal import WAL
from .protocol import parse, ok, value, integer, error


def _dispatch(store: KVStore, cmd: str, args: list[str]) -> str:
    try:
        if cmd == "SET":
            if len(args) < 2:
                return error("usage: SET key value [EX seconds]")
            ttl = float(args[3]) if len(args) == 4 and args[2].upper() == "EX" else None
            store.set(args[0], args[1], ttl=ttl)
            return ok()

        if cmd == "GET":
            if len(args) != 1:
                return error("usage: GET key")
            return value(store.get(args[0]))

        if cmd == "DELETE":
            if len(args) != 1:
                return error("usage: DELETE key")
            return integer(int(store.delete(args[0])))

        if cmd == "INCR":
            if len(args) != 1:
                return error("usage: INCR key")
            return integer(store.incr(args[0]))

        if cmd == "KEYS":
            return value(" ".join(store.keys()) or "(empty)")

        return error(f"unknown command '{cmd}'")

    except Exception as e:
        return error(str(e))


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        print(f"[+] {self.client_address}")
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
                self.wfile.write(_dispatch(self.server.store, cmd, args).encode())
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            print(f"[-] {self.client_address}")


class KVServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, store: KVStore, host: str = config.SERVER_HOST, port: int = config.SERVER_PORT):
        self.store = store
        super().__init__((host, port), _Handler)


if __name__ == "__main__":
    wal   = WAL()
    store = KVStore(wal=wal)
    server = KVServer(store)
    print(f"listening on {config.SERVER_HOST}:{config.SERVER_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()
        wal.close()
