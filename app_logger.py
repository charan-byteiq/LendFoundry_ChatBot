import logging
import sys

logger = logging.getLogger("lendfoundry")

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)  # force stdout
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.setLevel(logging.DEBUG)
logger.propagate = True