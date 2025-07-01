import argparse
import sys
from typing import Optional, Callable

from client import LinuxCommandClient


def get_connection_code() -> str:
    return input("Enter connection code: ").strip()


def prompt_for_connection_code() -> str:
    while True:
        connection_code = get_connection_code()
        if connection_code:
            return connection_code
        print("Connection code is required.")


def create_connection_code_callback() -> Callable[[], str]:
    def get_new_connection_code() -> str:
        print("Connection failed! Please enter a new connection code.\n")
        return prompt_for_connection_code()
    return get_new_connection_code


def main() -> None:    
    connection_code = None
    connection_code_callback = None

    connection_code = prompt_for_connection_code()
    connection_code_callback = create_connection_code_callback()
    
    # Initialize and run the client
    client = LinuxCommandClient(
        server_url="https://llinux-back.onrender.com",
        websocket_url="wss://llinux-back.onrender.com",
        device_id=None,
        connection_code=connection_code,
        connection_code_callback=connection_code_callback
    )
    
    try:
        client.run()
    except Exception as e:
        print(f"Failed to run client: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()