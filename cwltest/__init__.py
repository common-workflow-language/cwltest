"""Run CWL descriptions with a cwl-runner, and look for expected output."""

import logging
import threading

UNSUPPORTED_FEATURE = 33
DEFAULT_TIMEOUT = 600  # 10 minutes
REQUIRED = "required"

logger = logging.getLogger("cwltest")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

templock = threading.Lock()
