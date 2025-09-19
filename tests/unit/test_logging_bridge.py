import logging

from src.logging.gui_bridge import GuiLogRecord, QtSignalHandler


def test_gui_log_record_from_logging_record() -> None:
    logger = logging.getLogger("test.gui")
    record = logging.LogRecord(
        name=logger.name,
        level=logging.WARNING,
        pathname=__file__,
        lineno=10,
        msg="Sample message",
        args=(),
        exc_info=None,
        func=None,
    )

    gui_record = GuiLogRecord.from_record(record)

    assert gui_record.level == "warning"
    assert "Sample message" in gui_record.message
    assert gui_record.logger == "test.gui"
    assert gui_record.timestamp.endswith("+00:00")


def test_qt_signal_handler_emits_gui_log_record(monkeypatch) -> None:
    captured: list[GuiLogRecord] = []
    handler = QtSignalHandler(captured.append)

    logger = logging.getLogger("test.gui.handler")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Hello GUI")

    logger.removeHandler(handler)

    assert len(captured) == 1
    assert captured[0].message.endswith("Hello GUI")
    assert captured[0].level == "info"
