import logging

def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """Set up a logger with a consistent format."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger