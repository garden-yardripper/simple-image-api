import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # prevent log duplication
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    )
    
    import os
    logs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_path, exist_ok=True)
    
    # rotating file
    file_handler = RotatingFileHandler(
        os.path.join(logs_path, "apilogs.log"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.getLogger("watchfiles").setLevel(logging.WARNING)