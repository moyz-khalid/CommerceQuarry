from loguru import logger
import sys

# Configure logger format and level
def configure_logger():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time} | {level} | {message}")
    return logger
