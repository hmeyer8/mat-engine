import logging
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Create or fetch a configured logger.

    Args:
        name: Optional logger name.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name if name else __name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
