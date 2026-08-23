"""
Simple centralized logger. In a RAG application, every step (upload,
chunking, embedding, retrieval, LLM call) needs to be logged —
otherwise, when an answer comes out wrong, it becomes hard to debug
since it's unclear which step failed.
"""

import logging
from app.config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:  # avoid adding duplicate handlers
        logger.setLevel(LOG_LEVEL)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent messages from being passed up to the root logger,
        # which would otherwise cause each log line to print twice
        # (once from this handler, once from Flask's root handler).
        logger.propagate = False

    return logger