import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional
from pathlib import Path

# Setup logging directory
LOG_DIR = os.path.join(os.path.expanduser("~"), ".linux_command_client")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "client.log")

# Cache for configured loggers to avoid duplicate handlers
_configured_loggers = set()

def _load_env_file() -> dict:
    """Load environment variables from .env file.
    
    Returns:
        Dictionary of environment variables from .env file
    """
    env_vars = {}
    
    # Look for .env file in current directory first, then in parent directories
    current_dir = Path.cwd()
    env_file = None
    
    for path in [current_dir] + list(current_dir.parents):
        potential_env = path / ".env"
        if potential_env.exists():
            env_file = potential_env
            break
    
    if env_file and env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
        except Exception as e:
            print(f"Warning: Could not read .env file: {e}")
    
    return env_vars

def _is_production_mode() -> bool:
    """Check if the application is running in production mode.
    
    Returns:
        True if in production mode, False otherwise
    """
    env_vars = _load_env_file()
    
    # Check various common environment variable names
    env_mode = (
        env_vars.get('ENVIRONMENT', '').lower() or
        env_vars.get('ENV', '').lower() or
        env_vars.get('NODE_ENV', '').lower() or
        env_vars.get('APP_ENV', '').lower() or
        os.environ.get('ENVIRONMENT', '').lower() or
        os.environ.get('ENV', '').lower()
    )
    
    return env_mode in ['production', 'prod']

class ProductionLogger:
    """A no-op logger for production mode that does nothing."""
    
    def __init__(self, name: str):
        self.name = name
    
    def debug(self, *args, **kwargs):
        pass
    
    def info(self, *args, **kwargs):
        pass
    
    def warning(self, *args, **kwargs):
        pass
    
    def warn(self, *args, **kwargs):
        pass
    
    def error(self, *args, **kwargs):
        pass
    
    def exception(self, *args, **kwargs):
        pass
    
    def critical(self, *args, **kwargs):
        pass
    
    def log(self, *args, **kwargs):
        pass
    
    def setLevel(self, *args, **kwargs):
        pass
    
    def addHandler(self, *args, **kwargs):
        pass
    
    def removeHandler(self, *args, **kwargs):
        pass

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Name for the logger
        
    Returns:
        A configured logger instance (no-op logger in production mode)
    """
    # Check if we're in production mode
    if _is_production_mode():
        return ProductionLogger(name)
    
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been added yet
    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add file handler with rotation
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False
        
        # Mark as configured
        _configured_loggers.add(name)
    
    return logger

# Example usage:
if __name__ == "__main__":
    # Create a logger
    logger = get_logger("test_logger")
    
    # These will only work in development mode
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    print(f"Production mode: {_is_production_mode()}")