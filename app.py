import argparse
import sys
from typing import Optional, Callable

from client import LinuxCommandClient


def get_connection_code() -> str:
    """Prompt the user for a connection code.
    
    Returns:
        The connection code entered by the user
    """
    return input("Enter connection code: ").strip()


def prompt_for_connection_code() -> str:
    """Prompt for connection code until a valid one is provided."""
    while True:
        connection_code = get_connection_code()
        if connection_code:
            return connection_code
        print("Connection code is required.")


def create_connection_code_callback() -> Callable[[], str]:
    """Create a callback function for getting connection codes."""
    def get_new_connection_code() -> str:
        print("Connection failed! Please enter a new connection code.\n")
        return prompt_for_connection_code()
    return get_new_connection_code


def main() -> None:
    """Main entry point for the Linux Command Execution Client."""
    parser = argparse.ArgumentParser(description="Linux Command Execution Client")
    parser.add_argument(
        "--server", 
        default="http://localhost:3000", 
        help="HTTP server URL"
    )
    parser.add_argument(
        "--ws", 
        default="ws://localhost:3000", 
        help="WebSocket server URL"
    )
    parser.add_argument(
        "--device-id", 
        help="Custom device ID (MAC address used if not provided)"
    )
    parser.add_argument(
        "--skip-code", 
        action="store_true", 
        help="Skip the connection code prompt"
    )
    
    args = parser.parse_args()
    
    # Handle connection code
    connection_code = None
    connection_code_callback = None
    
    if not args.skip_code:
        connection_code = prompt_for_connection_code()
        connection_code_callback = create_connection_code_callback()
    
    # Initialize and run the client
    client = LinuxCommandClient(
        server_url=args.server,
        websocket_url=args.ws,
        device_id=args.device_id,
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