#!/usr/bin/env python3
import argparse
import sys
from client import LinuxCommandClient

def get_connection_code():
    """Prompt the user for a connection code.
    
    Returns:
        str: The connection code entered by the user
    """
    return input("Enter connection code: ").strip()

def main():
    """Main entry point for the Linux Command Execution Client."""
    parser = argparse.ArgumentParser(description="Linux Command Execution Client")
    parser.add_argument("--server", default="http://localhost:3000", help="HTTP server URL")
    parser.add_argument("--ws", default="ws://localhost:3000", help="WebSocket server URL")
    parser.add_argument("--device-id", help="Custom device ID (uuid generated if not provided)")
    parser.add_argument("--skip-code", action="store_true", help="Skip the connection code prompt")
    args = parser.parse_args()
    
    connection_code = None
    
    # Get connection code unless skipped
    if not args.skip_code:
        connection_code = get_connection_code()
        if not connection_code:
            print("Connection code is required. Exiting.")
            sys.exit(1)
    
    # Initialize and run the client with the connection code
    client = LinuxCommandClient(
        args.server, 
        args.ws, 
        args.device_id,
        connection_code=connection_code
    )
    client.run()

if __name__ == "__main__":
    main()
