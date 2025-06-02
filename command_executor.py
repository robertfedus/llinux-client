import subprocess
from logger import get_logger

logger = get_logger("CommandExecutor")

def execute_command(cmd, timeout=90):
    """Execute a shell command and return its output.
    
    Args:
        cmd: The command string to execute
        timeout: Maximum execution time in seconds (default: 90)
        
    Returns:
        tuple: (output, success)
            - output: Combined stdout and stderr output
            - success: Boolean indicating if command succeeded
    """
    try:
        # Execute the command
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate(timeout=timeout)
        success = process.returncode == 0
        
        # Combine stdout and stderr
        output = stdout
        if stderr:
            output += f"\n--- stderr ---\n{stderr}"
        
        # Truncate output if it's too large
        output = truncate_output(output)
        
        return output, success
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds: {cmd}")
        # Truncate output for timeouts
        output = truncate_output(f"Command execution timed out after {timeout} seconds")
        return output, False

def truncate_output(output, max_length=8192, max_lines=100):
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