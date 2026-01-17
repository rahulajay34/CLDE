import logging
import sys
import os

def setup_logger(name="EdTechCore", level=logging.INFO):
    """
    Sets up a configured logger with console output.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers if already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler (Optional, creates app.log)
    try:
        file_handler = logging.FileHandler("app.log", encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass # Fallback if file permission issues
        
    return logger

# Singleton instance
logger = setup_logger()
