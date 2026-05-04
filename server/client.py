import socket
import config


def main() -> None:
    with socket.create_connection((config.SERVER_HOST, config.SERVER_PORT)) as sock:
        reader = sock.makefile("rb")
        print(f"connected to {config.SERVER_HOST}:{config.SERVER_PORT}  (quit to exit)")
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
