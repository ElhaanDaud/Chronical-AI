import logging
import sys


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("chronicle")

    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)

    return logger


logger = setup_logging()
