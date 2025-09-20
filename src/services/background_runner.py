from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Optional, Any

from PySide6.QtCore import QTimer, QObject, Signal, QMetaObject, Qt


# Simple global thread pool for background tasks that must not block the UI
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bg")


class _UiInvoker(QObject):
    """Helper QObject that lives on the UI thread to marshal callbacks safely."""
    callback_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.callback_signal.connect(self._execute_callback, Qt.QueuedConnection)

    def _execute_callback(self, callback):
        try:
            callback()
        except Exception as e:
            print(f"ERROR: Exception in UI callback: {e}")
            import traceback
            traceback.print_exc()
            # Try to show a basic error dialog as last resort
            try:
                from PySide6.QtWidgets import QMessageBox, QApplication
                if QApplication.instance():
                    QMessageBox.critical(None, "Application Error", f"An unexpected error occurred: {e}")
            except Exception:
                print("ERROR: Failed to show error dialog")


# Create an invoker instance. This module should be imported on the UI thread,
# so the object affinity will be the UI thread. If imported earlier, it will
# still be moved to the thread that creates QApplication later when first used.
_invoke_target = _UiInvoker()


def _on_ui(cb: Callable[[], None]) -> None:
    # Use Qt signal/slot mechanism for reliable cross-thread callback execution
    _invoke_target.callback_signal.emit(cb)


def run_bg(
    fn: Callable[[], Any],
    *,
    on_result: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[BaseException], None]] = None,
) -> Future:
    """Run a callable in background and post callbacks on the UI thread.

    - fn: the work function to execute off the UI thread
    - on_result: called on the UI thread with the return value
    - on_error: called on the UI thread with the exception if fn raises
    """
    fut: Future = _executor.submit(fn)

    def _done_cb(f: Future) -> None:
        try:
            res = f.result()
        except BaseException as exc:  # deliver error on UI thread
            if on_error is not None:
                # Capture exc by value to avoid closure variable scope issues
                captured_exc = exc
                def error_callback():
                    on_error(captured_exc)
                _on_ui(error_callback)
            return
        if on_result is not None:
            _on_ui(lambda: on_result(res))

    fut.add_done_callback(_done_cb)
    return fut

