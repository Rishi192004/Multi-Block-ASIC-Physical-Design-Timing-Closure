"""Structured logging setup for EDA-Genius."""

import sys
import logging
from pathlib import Path
from typing import Optional


class CorrelationLogger:
    """Standard Python structured logger with run_id and stage context."""
    def __init__(self, run_id: Optional[str] = None, stage: Optional[str] = None):
        self.run_id = run_id or "system"
        self.stage = stage or "init"
        self.logger = logging.getLogger("eda_genius")
        if not self.logger.handlers:
            self._setup_logger()

    def _setup_logger(self):
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [run_id=%(run_id)s] [stage=%(stage)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def bind(self, run_id: Optional[str] = None, stage: Optional[str] = None) -> "CorrelationLogger":
        return CorrelationLogger(
            run_id=run_id if run_id is not None else self.run_id,
            stage=stage if stage is not None else self.stage
        )

    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra={"run_id": self.run_id, "stage": self.stage, **kwargs})

    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra={"run_id": self.run_id, "stage": self.stage, **kwargs})

    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra={"run_id": self.run_id, "stage": self.stage, **kwargs})

    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra={"run_id": self.run_id, "stage": self.stage, **kwargs})


logger = CorrelationLogger()
