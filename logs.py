import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger.json import JsonFormatter
from config import settings
import os

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # prevent log duplication
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    )
    
    os.makedirs(settings.log_directory, exist_ok=True)
    
    # rotating file
    file_handler = RotatingFileHandler(
        os.path.join(settings.log_directory, "apilogs.log"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # json
    json_formatter = JsonFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        json_indent=4
    )
    json_file_handler = RotatingFileHandler(
        os.path.join(settings.log_directory, "apilogs.json.log"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    json_file_handler.setFormatter(json_formatter)
    json_file_handler.setLevel(logging.DEBUG)
    logger.addHandler(json_file_handler)
    
    # console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.getLogger("watchfiles").setLevel(logging.WARNING)