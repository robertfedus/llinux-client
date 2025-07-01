import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = os.path.join(os.path.expanduser("~"), ".linux_command_client")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "client.log")

_configured_loggers = set()

def _load_env_file() -> dict:
    env_vars = {}
    
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
    env_vars = _load_env_file()
    
    env_mode = (env_vars.get('ENVIRONMENT', '').lower())
    
    return env_mode in ['production', 'prod']

class ProductionLogger:    
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
    if _is_production_mode():
        return ProductionLogger(name)
    
    logger = logging.getLogger(name)
    
    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024, 
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        logger.propagate = False
        
        _configured_loggers.add(name)
    
    return logger
