"""A minimal interactive client — type a command, see the reply."""
import socket
from kvstore import config


def main() -> None:
    conf = config.load()
    with socket.create_connection((conf.server_host, conf.server_port)) as sock:
        reader = sock.makefile("rb")
        print(f"connected to {conf.server_host}:{conf.server_port}  (quit to exit)")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.lower() == "quit":
                break
            sock.sendall((line + "\r\n").encode())
            print(reader.readline().decode().strip())
    print("disconnected.")


if __name__ == "__main__":
    main()
