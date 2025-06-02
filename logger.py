import logging
import os
from logging.handlers import RotatingFileHandler

# Setup logging directory
LOG_DIR = os.path.join(os.path.expanduser("~"), ".linux_command_client")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "client.log")

# Shared logger configuration
def get_logger(name):
    """Get a configured logger instance.
    
    Args:
        name: Name for the logger
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been added yet
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Add file handler
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(file_formatter)
        logger.addHandler(console_handler)
    
    return logger