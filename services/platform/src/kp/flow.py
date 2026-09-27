"""Request-flow events written to the API terminal as each stage runs."""

from __future__ import annotations

import json
import logging
import sys

_CONFIGURED = False


def configure_flow_logging() -> None:
    """Attach a stderr handler so flow events show up in the uvicorn terminal."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    logger = logging.getLogger("kp.flow")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True


def event(name: str, **fields: object) -> None:
    configure_flow_logging()
    parts = [f"event={name}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_field(value)}")
    logging.getLogger("kp.flow").info(" ".join(parts))


def _field(value: object) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) > 120:
        text = text[:117] + "..."
    if text == "" or any(character.isspace() for character in text):
        return json.dumps(text)
    return text
