import json
import threading
import time
import uuid
from typing import List, Optional, Tuple, Callable
import websocket

from logger import get_logger
from command_executor import execute_command
from system_information import SystemInformation


class LinuxCommandClient:
    """WebSocket client for executing Linux commands remotely."""
    
    # Constants
    CONNECTION_TIMEOUT = 0.5
    RECONNECTION_INTERVAL = 1.0
    REGISTRATION_TIMEOUT = 5.0  # Time to wait for registration response
    
    def __init__(
        self, 
        server_url: str, 
        websocket_url: str, 
        device_id: Optional[str] = None, 
        connection_code: Optional[str] = None,
        connection_code_callback: Optional[Callable[[], str]] = None
    ):
        """Initialize the Linux command client.
        
        Args:
            server_url: HTTP endpoint for the server (e.g., http://localhost:3000)
            websocket_url: WebSocket endpoint (e.g., ws://localhost:3000)
            device_id: Optional device ID. If not provided, MAC address will be used.
            connection_code: Connection code for device pairing
            connection_code_callback: Function to call when a new connection code is needed
        """
        self.server_url = server_url.rstrip('/')
        self.websocket_url = websocket_url
        self.device_id = device_id or str(uuid.getnode())
        self.connection_code = connection_code
        self.connection_code_callback = connection_code_callback
        
        # Connection state
        self._ws = None
        self._connected = False
        self._connecting = False
        self._shutdown_requested = False
        self._registration_failed = False
        self._registration_pending = False
        self._registration_start_time = None
        
        self._logger = get_logger("LinuxCommandClient")
        self._logger.info(f"Initializing client with device ID: {self.device_id}")
        
    @property
    def connected(self) -> bool:
        """Check if the client is connected."""
        return self._connected
    
    def connect(self) -> None:
        """Establish WebSocket connection and register the device."""
        if self._connecting:
            self._logger.debug("Connection attempt already in progress, skipping")
            return
            
        self._connecting = True
        self._logger.info(f"Connecting to {self.websocket_url}")
        
        try:
            self._ws = websocket.WebSocketApp(
                self.websocket_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Start WebSocket connection in a separate thread
            ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
            ws_thread.start()
            
            # Give some time for connection to establish
            time.sleep(self.CONNECTION_TIMEOUT)
        except Exception as e:
            self._logger.error(f"Failed to connect: {e}")
        finally:
            self._connecting = False
    
    def disconnect(self) -> None:
        """Close the WebSocket connection."""
        self._shutdown_requested = True
        if self._ws:
            self._ws.close()
    
    def run(self) -> None:
        """Run the client, maintaining connection to the server."""
        try:
            self.connect()
            
            while not self._shutdown_requested:
                if self._connected:
                    self._send_system_information()
                elif not self._connecting:
                    # Check if registration failed and we need a new connection code
                    if self._registration_failed and self.connection_code_callback:
                        self._logger.info("Registration failed. Requesting new connection code...")
                        try:
                            self.connection_code = self.connection_code_callback()
                            self._registration_failed = False
                            self._logger.info("New connection code obtained. Attempting to reconnect...")
                        except KeyboardInterrupt:
                            self._logger.info("User cancelled connection code input")
                            break
                        except Exception as e:
                            self._logger.error(f"Error getting new connection code: {e}")
                            break
                    
                    if not self._registration_failed:
                        self._logger.info("Not connected. Attempting to reconnect...")
                        self._reconnect()
                
                # Check for registration timeout
                if self._registration_pending and self._registration_start_time:
                    if time.time() - self._registration_start_time > self.REGISTRATION_TIMEOUT:
                        self._logger.warning("Registration timeout - treating as failed")
                        self._registration_failed = True
                        self._registration_pending = False
                        self._connected = False
                        if self._ws:
                            self._ws.close()
                
                time.sleep(self.RECONNECTION_INTERVAL)
        
        except KeyboardInterrupt:
            self._logger.info("Shutting down client...")
        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
        finally:
            self.disconnect()
    
    def _reconnect(self) -> None:
        """Attempt to reconnect to the server."""
        if not self._connecting and not self._connected and not self._shutdown_requested:
            self._logger.info("Attempting to reconnect...")
            try:
                self.connect()
            except Exception as e:
                self._logger.error(f"Reconnection failed: {e}")
    
    def _on_message(self, ws, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            self._logger.info(f"Received message: {data}")
            
            message_type = data.get('type')
            
            if message_type == 'connected':
                self._register_device()
            elif message_type == 'registered':
                self._handle_registration_response(data)
            elif message_type == 'execute':
                self._handle_execute_command(data)
            else:
                self._logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            self._logger.error(f"Failed to parse message: {message}")
        except Exception as e:
            self._logger.error(f"Error in message handler: {e}")
    
    def _on_error(self, ws, error) -> None:
        """Handle WebSocket errors."""
        self._logger.error(f"WebSocket error: {error}")
        self._connected = False
        self._connecting = False
    
    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """Handle WebSocket connection close."""
        self._logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self._connected = False
        self._connecting = False
    
    def _on_open(self, ws) -> None:
        """Handle WebSocket connection open."""
        self._logger.info("WebSocket connection established")
    
    def _register_device(self) -> None:
        """Register the device with the server via WebSocket."""
        if not self._ws:
            self._logger.error("Cannot register: WebSocket not available")
            return
            
        try:
            registration_data = {
                "type": "register",
                "deviceId": self.device_id,
            }
            
            if self.connection_code:
                registration_data["connectionCode"] = self.connection_code
            
            self._ws.send(json.dumps(registration_data))
            self._logger.info(f"Sent registration for device ID: {self.device_id}")
            
            # Start tracking registration timeout
            self._registration_pending = True
            self._registration_start_time = time.time()
            
        except Exception as e:
            self._logger.error(f"Failed to register device: {e}")
    
    def _handle_registration_response(self, data: dict) -> None:
        """Handle device registration response."""
        self._registration_pending = False
        self._registration_start_time = None
        
        if data.get('success'):
            self._logger.info("Device successfully registered")
            print("Device connected successfully to LLinux!")
            self._connected = True
            self._registration_failed = False
        else:
            self._logger.error("Device registration failed!")
            self._connected = False
            self._registration_failed = True
    
    def _handle_execute_command(self, data: dict) -> None:
        """Handle command execution request."""
        command_id = data.get('commandId')
        commands = data.get('commands', [])
        
        if not commands:
            self._logger.warning("Received empty command list")
            return
        
        self._execute_commands(commands, command_id)
    
    def _execute_commands(self, commands: List[str], command_id: str) -> None:
        """Execute the received commands and send back results."""
        for i, cmd in enumerate(commands):
            self._logger.info(f"Executing command {i} (batch {command_id}): {cmd}")
            
            try:
                output, success = execute_command(cmd)
                self._send_command_results(command_id, i, cmd, output, success)
                
            except Exception as e:
                error_msg = f"Error executing command: {e}"
                self._logger.error(f"Error executing command {i} (batch {command_id}): {e}")
                self._send_command_results(command_id, i, cmd, error_msg, False)
    
    def _send_command_results(
        self, 
        command_id: str, 
        index: int, 
        command: str, 
        output: str, 
        success: bool
    ) -> None:
        """Send command execution results back to the server via WebSocket."""
        if not self._ws or not self._connected:
            self._logger.error("Cannot send results: WebSocket not connected")
            return
            
        try:
            result_data = {
                "type": "command_result",
                "deviceId": self.device_id,
                "commandId": command_id,
                "index": index,
                "command": command,
                "output": output,
                "success": success
            }
            
            self._ws.send(json.dumps(result_data))
            self._logger.info(f"Successfully sent results for command {index} (batch {command_id})")
            
        except Exception as e:
            self._logger.error(f"Error sending command results via WebSocket: {e}")

    def _send_system_information(self) -> None:
        """Send system information to the server."""
        if not self._ws or not self._connected:
            self._logger.error("Cannot send system info: WebSocket not connected")
            return
        
        try:
            system_info = SystemInformation()
            
            info_data = {
                "type": "system_information",
                "deviceId": self.device_id,
                "system_information": system_info.collect_all_info(),
                "system_resources": system_info.collect_all_resources()
            }
            
            self._ws.send(json.dumps(info_data))
            # self._logger.info("Successfully sent system information")
            
        except Exception as e:
            self._logger.error(f"Error sending system information via WebSocket: {e}")