import websocket # type: ignore
import json
import threading
import time
import uuid
from logger import get_logger
from command_executor import execute_command
from system_information import SystemInformation

logger = get_logger("LinuxCommandClient")

class LinuxCommandClient:
    def __init__(self, server_url, websocket_url, device_id=None, connection_code=None):
        """Initialize the Linux command client.
        
        Args:
            server_url: HTTP endpoint for the server (e.g., http://localhost:3000)
            websocket_url: WebSocket endpoint (e.g., ws://localhost:3000)
            device_id: Optional device ID. If not provided, a UUID will be generated.
            connection_code: Connection code for device pairing
        """
        self.server_url = server_url.rstrip('/')
        self.websocket_url = websocket_url
        # self.device_id = device_id or str(uuid.uuid4())
        self.device_id = device_id or uuid.getnode()
        self.connection_code = connection_code
        self.ws = None
        self.connected = False
        self.connecting = False  # Flag to prevent concurrent connection attempts
        logger.info(f"Initializing client with device ID: {self.device_id}")
        
    def connect(self):
        """Establish WebSocket connection and register the device."""
        # Prevent concurrent connection attempts
        if self.connecting:
            logger.debug("Connection attempt already in progress, skipping")
            return
            
        self.connecting = True
        logger.info(f"Connecting to {self.websocket_url}")
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                logger.info(f"Received message: {data}")
                
                if data.get('type') == 'connected':
                    # Register the device after connection
                    self._register_device()
                
                elif data.get('type') == 'registered':
                    if data.get('success', False):
                        logger.info("Device successfully registered")
                        self.connected = True
                    else:
                        logger.error(f"Device registration failed: {data.get('message', 'Unknown error')}")
                        self.connected = False
                
                elif data.get('type') == 'execute':
                    # Handle command execution request
                    command_id = data.get('commandId')
                    commands = data.get('commands', [])
                    self._handle_commands(commands, command_id)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse message: {message}")
            except Exception as e:
                logger.error(f"Error in message handler: {str(e)}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            self.connected = False
            self.connecting = False
        
        def on_close(ws, close_status_code, close_msg):
            logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
            self.connected = False
            self.connecting = False
            # Reconnection will be handled by the run loop
        
        def on_open(ws):
            logger.info("WebSocket connection established")
            # Note: Registration will happen when we receive the 'connected' message
        
        # Set up WebSocket connection
        self.ws = websocket.WebSocketApp(
            self.websocket_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Start WebSocket connection in a separate thread
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
        
        # Give some time for connection to establish before returning
        time.sleep(0.5)
        self.connecting = False
    
    def _reconnect(self):
        """Attempt to reconnect to the server."""
        if not self.connecting and not self.connected:
            logger.info("Attempting to reconnect...")
            try:
                self.connect()
            except Exception as e:
                logger.error(f"Reconnection failed: {str(e)}")
                self.connecting = False
    
    def _register_device(self):
        """Register the device with the server via WebSocket."""
        if self.ws:
            try:
                registration_data = {
                    "type": "register",
                    "deviceId": self.device_id,
                }
                
                # Add connection code if available
                if self.connection_code:
                    registration_data["connectionCode"] = self.connection_code
                
                self.ws.send(json.dumps(registration_data))
                logger.info(f"Sent registration for device ID: {self.device_id}")
            except Exception as e:
                logger.error(f"Failed to register device: {str(e)}")
    
    def _handle_commands(self, commands, command_id):
        """Execute the received commands and send back results.
        
        Args:
            commands: List of command strings to execute.
            command_id: The ID of this command batch.
        """
        if not commands:
            logger.warning("Received empty command list")
            return
        
        for i, cmd in enumerate(commands):
            logger.info(f"Executing command {i} (batch {command_id}): {cmd}")
            
            try:
                # Execute the command
                output, success = execute_command(cmd)
                
                # Send results back to server via WebSocket
                self._send_command_results_ws(command_id, i, cmd, output, success)
                
            except Exception as e:
                logger.error(f"Error executing command {i} (batch {command_id}): {str(e)}")
                # Truncate error output too
                error_msg = f"Error executing command: {str(e)}"
                output = self._truncate_output(error_msg)
                
                self._send_command_results_ws(
                    command_id,
                    i,
                    cmd,
                    output,
                    False
                )
    
    def _truncate_output(self, output, max_length=8192, max_lines=100):
        """Truncate command output if it exceeds limits.
        
        Args:
            output: The command output string
            max_length: Maximum number of characters (default: 8KB)
            max_lines: Maximum number of lines (default: 100)
            
        Returns:
            Truncated output string with indicator if truncation occurred
        """
        if not output:
            return output
            
        # Check if output exceeds line limit
        lines = output.splitlines()
        if len(lines) > max_lines:
            truncated_lines = lines[:max_lines]
            lines_truncated = len(lines) - max_lines
            truncated_lines.append(f"\n... output truncated ({lines_truncated} more lines) ...")
            output = "\n".join(truncated_lines)
            
        # Check if output exceeds character limit
        if len(output) > max_length:
            chars_truncated = len(output) - max_length
            output = output[:max_length] + f"\n... output truncated ({chars_truncated} more characters) ..."
            
        return output
        
    def _send_command_results_ws(self, command_id, index, command, output, success):
        """Send command execution results back to the server via WebSocket.
        
        Args:
            command_id: ID of the command batch
            index: Index of this command in the batch
            command: The command that was executed
            output: Command output (stdout/stderr)
            success: Boolean indicating if command succeeded
        """
        if not self.ws or not self.connected:
            logger.error("Cannot send results: WebSocket not connected")
            return
            
        try:
            self.ws.send(json.dumps({
                "type": "command_result",
                "deviceId": self.device_id,
                "commandId": command_id,
                "index": index,
                "command": command,
                "output": output,
                "success": success
            }))
            
            logger.info(f"Successfully sent results for command {index} (batch {command_id})")
        
        except Exception as e:
            logger.error(f"Error sending command results via WebSocket: {str(e)}")

    def _send_system_information(self):
        if not self.ws or not self.connected:
            logger.error("Cannot send results: WebSocket not connected")
            return
        
        system_information = SystemInformation()
            
        try:
            self.ws.send(json.dumps({
                "type": "system_information",
                "deviceId": self.device_id,
                "system_information": system_information.collect_all_info(),
                "system_resources": system_information.collect_all_resources()
            }))
            
            logger.info(f"Successfully sent system information")
        
        except Exception as e:
            logger.error(f"Error sending system information via WebSocket: {str(e)}")
    
    def run(self):
        """Run the client, maintaining connection to the server."""
        try:
            # Initial connection
            self.connect()
            
            # Keep the main thread alive
            while True:
                if self.connected:
                   self._send_system_information() 

                if not self.connected and not self.connecting:
                    logger.info("Not connected. Attempting to reconnect...")
                    self._reconnect()
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Shutting down client...")
            if self.ws:
                self.ws.close()
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            if self.ws:
                self.ws.close()