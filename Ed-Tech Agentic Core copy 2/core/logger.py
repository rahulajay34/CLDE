import logging
import sys
import os
import json
import time

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for structured logging.
    """
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        # Merge extra attributes if passed in extra={}
        if hasattr(record, "props"):
            log_obj.update(record.props)

        return json.dumps(log_obj)

def setup_logger(name="EdTechCore", level=logging.INFO):
    """
    Sets up a configured logger with console output and daily file rotation.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers if already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Formatter
    formatter = JSONFormatter(datefmt='%Y-%m-%dT%H:%M:%SZ')
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    try:
        os.makedirs("logs", exist_ok=True)
        # Simple file handler (log rotation could be added here)
        log_file = f"logs/app_{time.strftime('%Y-%m-%d')}.jsonl"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logger: {e}")
        
    return logger

# Singleton instance
logger = setup_logger()
# Usage: logger.info("Event", extra={"props": {"user_id": 123, "cost": 0.05}})
