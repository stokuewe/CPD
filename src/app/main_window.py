from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QTextEdit,
    QLabel,
    QProgressDialog,
    QMenu,
    QMenuBar,
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPalette, QAction


class MainWindow(QMainWindow):
    """Main application window with Startup view for M1.

    Contains:
    - Recent projects list
    - Actions: Open Project, Create Project, Clear Recent
    - Log pane (read-only)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CPD - Common Project Database")
        self._controller = None

        # Menu bar
        self._build_menu()

        # Central layout
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addWidget(QLabel("Recent projects"))
        self.recent_list = QListWidget()
        # Right-click context menu for Recent list
        self.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._on_recent_context_menu)
        root.addWidget(self.recent_list, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_open = QPushButton("Open Project")
        self.btn_create = QPushButton("Create Project")
        self.btn_close = QPushButton("Close Project")
        self.btn_clear = QPushButton("Clear Recent")
        btn_row.addWidget(self.btn_open)
        btn_row.addWidget(self.btn_create)
        btn_row.addWidget(self.btn_close)
        btn_row.addWidget(self.btn_clear)
        root.addLayout(btn_row)

        root.addWidget(QLabel("Log"))
        self.log_pane = QTextEdit()
        self.log_pane.setReadOnly(True)
        # Busy/progress state
        self._busy = False
        self.progress_dialog = None
        self._busy_timer = QTimer(self)
        self._busy_timer.setSingleShot(True)
        self._busy_timer.timeout.connect(self._on_busy_timer)

        root.addWidget(self.log_pane, stretch=1)

        # Disable actions until wired by controller
        self.btn_open.setEnabled(True)
        self.btn_create.setEnabled(True)
        self.btn_close.setEnabled(False)  # Disabled until project is open
        self.btn_clear.setEnabled(True)

    # Wiring ---------------------------------------------------------
    def set_controller(self, controller) -> None:
        self._controller = controller
        # Wire signals to controller methods if available
        if hasattr(controller, "on_open_clicked"):
            self.btn_open.clicked.connect(controller.on_open_clicked)
        if hasattr(controller, "on_create_clicked"):
            self.btn_create.clicked.connect(controller.on_create_clicked)
        if hasattr(controller, "on_clear_recent_clicked"):
            self.btn_clear.clicked.connect(controller.on_clear_recent_clicked)
        if hasattr(controller, "on_close_project_clicked"):
            self.btn_close.clicked.connect(controller.on_close_project_clicked)
        # Menu actions
        if hasattr(controller, "on_settings_clicked") and hasattr(self, "act_settings"):
            try:
                self.act_settings.triggered.connect(controller.on_settings_clicked)
            except Exception:
                pass
        if hasattr(controller, "on_close_project_clicked") and hasattr(self, "act_close_project"):
            try:
                self.act_close_project.triggered.connect(controller.on_close_project_clicked)
            except Exception:
                pass
        # Allow opening recent items by double-click or Enter
        if hasattr(controller, "on_recent_activated"):
            try:
                # Route through a guard that handles None items safely
                self.recent_list.itemActivated.connect(self._on_recent_item_activated)
                self.recent_list.itemDoubleClicked.connect(self._on_recent_item_activated)
            except Exception:
                pass
        # Expose remove handler presence for context menu
        self._has_remove = hasattr(controller, "on_recent_remove")

    # UI helpers -----------------------------------------------------
    def show_recent(self, entries: list[dict]) -> None:
        self.recent_list.clear()
        for e in entries:
            self.recent_list.addItem(e.get("path", ""))
        # Ensure no implicit selection at startup/refresh
        try:
            self.recent_list.clearSelection()
            self.recent_list.setCurrentRow(-1)
        except Exception:
            pass

    def _on_recent_item_activated(self, item) -> None:  # pragma: no cover - UI wiring stub
        if item is None or self._controller is None:
            return
        if hasattr(self._controller, "on_recent_activated"):
            try:
                self._controller.on_recent_activated(item.text())
            except Exception:
                pass

    def _is_dark_background(self) -> bool:
        pal = self.log_pane.palette()
        c = pal.color(self.log_pane.backgroundRole())
        if not c.isValid():
            c = pal.color(QPalette.Base)
        luma = 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
        return luma < 128

    def _color_for_level(self, level: str) -> str:
        dark = self._is_dark_background()
        if dark:
            mapping = {"INFO": "#eeeeee", "WARN": "#ffd166", "ERROR": "#ff6b6b"}
        else:
            mapping = {"INFO": "#111111", "WARN": "#a45500", "ERROR": "#960000"}
        return mapping.get(level.upper(), mapping["INFO"])

    def append_log(self, level: str, message: str) -> None:
        color = self._color_for_level(level)
        self.log_pane.append(f"<span style='color:{color}'>[{level}] {message}</span>")

    # Responsiveness helpers -----------------------------------------
    def start_busy(self) -> None:  # pragma: no cover - exercised via integration test
        if self._busy:
            return
        self._busy = True
        self.setCursor(Qt.BusyCursor)
        # Show progress dialog only if busy for >= 1s
        self._busy_timer.start(1000)

    def _on_busy_timer(self) -> None:  # pragma: no cover - exercised via integration test
        if not self._busy:
            return
        if self.progress_dialog is None:
            self.progress_dialog = QProgressDialog("Working...", "Cancel", 0, 0, self)
            self.progress_dialog.setWindowTitle("Please wait")
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setModal(False)  # Non-modal to allow event processing
        self.progress_dialog.show()

    def stop_busy(self) -> None:  # pragma: no cover - exercised via integration test
        if not self._busy:
            return
        self._busy = False
        self.unsetCursor()
        self._busy_timer.stop()
        if self.progress_dialog is not None:
            self.progress_dialog.hide()
            # Keep instance for potential reuse to avoid flicker; test checks visibility

    def is_busy(self) -> bool:  # pragma: no cover - exercised via integration test
        """Check if the UI is currently in busy state"""
        return self._busy

    def _on_recent_context_menu(self, pos: QPoint) -> None:  # pragma: no cover - UI interaction
        if not self._controller:
            return
        item = self.recent_list.itemAt(pos)
        if item is None:
            item = self.recent_list.currentItem()
        if item is None:
            return
        path = item.text()
        menu = QMenu(self)
        act_open = menu.addAction("Open")
        act_remove = menu.addAction("Remove from Recent") if getattr(self, "_has_remove", False) else None
        chosen = menu.exec(self.recent_list.mapToGlobal(pos))
        if chosen is act_open and hasattr(self._controller, "on_recent_activated"):
            self._controller.on_recent_activated(path)
        elif act_remove and chosen is act_remove and hasattr(self._controller, "on_recent_remove"):
            self._controller.on_recent_remove(path)

    def _build_menu(self) -> None:
        try:
            mb: QMenuBar = self.menuBar()

            # File menu
            menu_file = mb.addMenu("&File")
            self.act_close_project = QAction("&Close Project", self)
            self.act_close_project.setEnabled(False)  # Disabled until project is open
            menu_file.addAction(self.act_close_project)

            # Settings menu
            menu_settings = mb.addMenu("&Settings")
            self.act_settings = QAction("&Settings...", self)
            menu_settings.addAction(self.act_settings)
        except Exception:
            pass

    def set_project_open_state(self, is_open: bool) -> None:
        """Update UI to reflect whether a project is currently open"""
        self.btn_close.setEnabled(is_open)
        if hasattr(self, "act_close_project"):
            self.act_close_project.setEnabled(is_open)

