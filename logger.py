import logging
import sys

# Configure root logger to match uvicorn's simple format
logging.basicConfig(
    level="INFO",
    format="%(levelname)s:     %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Main application logger
logger = logging.getLogger("lendfoundary_chatbot")

# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
