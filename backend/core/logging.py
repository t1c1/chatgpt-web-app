import logging
import sys
from typing import Dict, Any
import structlog
from core.config import settings


def setup_logging():
    """Configure structured logging for the application."""

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure structlog
    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable logging for development
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str = None):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Context variables for request tracking
def add_request_context(request_id: str, user_id: str = None, **kwargs):
    """Add context variables for the current request."""
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=user_id,
        **kwargs
    )


def clear_request_context():
    """Clear request context variables."""
    structlog.contextvars.unbind_contextvars("request_id", "user_id")




