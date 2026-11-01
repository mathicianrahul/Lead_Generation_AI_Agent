import logging
import re
import sys
from typing import Any

# Patterns to mask sensitive information
SENSITIVE_PATTERNS = [
    re.compile(r'(api[-_]?key\s*[:=]\s*["\']?)([^"\'\s&]+)', re.IGNORECASE),
    re.compile(r'(token\s*[:=]\s*["\']?)([^"\'\s&]+)', re.IGNORECASE),
    re.compile(r'(secret\s*[:=]\s*["\']?)([^"\'\s&]+)', re.IGNORECASE),
    re.compile(r'(authorization\s*:\s*Bearer\s+)([^\s]+)', re.IGNORECASE),
]


class SanitizingFormatter(logging.Formatter):
    """Custom logging formatter that strips sensitive secrets from log strings."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r'\1[REDACTED]', sanitized)
        return sanitized


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures structured, sanitized logging for LeadPilot AI."""
    logger = logging.getLogger("leadpilot")
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = SanitizingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()

