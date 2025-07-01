import subprocess
from typing import Tuple

from logger import get_logger

logger = get_logger("CommandExecutor")


def execute_command(cmd: str, timeout: int = 10) -> Tuple[str, bool]:
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate(timeout=timeout)
        success = (process.returncode == 0)
        
        output = stdout
        if stderr:
            output += f"\n--- stderr ---\n{stderr}"
        
        output = truncate_output(output)
        
        return output, success
        
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"Command timed out and was killed: {cmd}")
        return "Command execution timed out and process was killed!", False
    except Exception as e:
        logger.error(f"Error executing command '{cmd}': {e}")
        return f"Error executing command: {e}", False


def truncate_output(
    output: str, 
    max_length: int = 8192, 
    max_lines: int = 100
) -> str:
    if not output:
        return output
        
    lines = output.splitlines()
    if len(lines) > max_lines:
        lines_truncated = len(lines) - max_lines
        truncated_lines = lines[:max_lines]
        truncated_lines.append(f"\n... output truncated ({lines_truncated} more lines) ...")
        output = "\n".join(truncated_lines)
        
    if len(output) > max_length:
        chars_truncated = len(output) - max_length
        output = output[:max_length] + f"\n... output truncated ({chars_truncated} more characters) ..."
        
    return output