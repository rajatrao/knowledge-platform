"""Flow events are one terminal line per stage."""

import logging

from kp.flow import event


def test_event_line_names_the_stage():
    lines = []

    class Capture(logging.Handler):
        def emit(self, record):
            lines.append(record.getMessage())

    logger = logging.getLogger("kp.flow")
    handler = Capture()
    logger.addHandler(handler)
    try:
        event("ask.received", session="sess-1", query="top complaints this week")
    finally:
        logger.removeHandler(handler)
    assert any("event=ask.received" in line and "session=sess-1" in line for line in lines)
    assert any("top complaints this week" in line for line in lines)
