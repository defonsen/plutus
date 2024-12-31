# utils/logger.py

import logging
import sys

logger = logging.getLogger("mev-arbitrage-bot")
logger.setLevel(logging.INFO)

# Console Handler
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)
