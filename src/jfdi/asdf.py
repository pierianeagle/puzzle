import logging
import logging.config
from pathlib import Path


def add(a, b):
    return a + b


def main():
    logging.config.fileConfig(
        "logging.ini", defaults={"filepath_log": Path("logs", "app")}
    )
    logger = logging.getLogger(__name__)

    logger.warning("beep")
    logger.error("boop")
    logger.critical("ASDFGHJKL;DFGHJKJGFDHSSGHJKH FDGDHGJKHJL")


if __name__ == "__main__":
    main()
