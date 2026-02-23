from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any


def setup_stderr_logging(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def load_sample_json(filename: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    path = root / "samples" / filename
    return json.loads(path.read_text(encoding="utf-8"))
