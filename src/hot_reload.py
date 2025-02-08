import importlib.util
import sys
import time
from pathlib import Path

from PyQt6 import QtWidgets, QtCore
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .utils import check_dependencies


class ElementTree(QtWidgets.QTreeWidget):
    element_selected = QtCore.pyqtSignal(QtWidgets.QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # Set up tree widget
        self.setHeaderLabel("UI Elements")
        self.setColumnCount(1)
        self.setHeaderHidden(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setIndentation(20)

        # Connect signals
        self.itemClicked.connect(self.on_item_clicked)

        # Style the tree
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 6px;
                border-radius: 2px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QTreeWidget::branch {
                background-color: white;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: url(vline.png) 0;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: url(branch-more.png) 0;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(branch-end.png) 0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
                color: #333;
            }
        """)

    def populate_tree(self, window):
        self.clear()
        self.widget_map = {}

        if not window:
            return

        root = QtWidgets.QTreeWidgetItem(self, [f"{window.__class__.__name__}"])
        self.widget_map[id(root)] = window
        self.add_widgets(window, root)
        self.expandAll()

    def add_widgets(self, parent_widget, parent_item):
        for child in parent_widget.findChildren(QtWidgets.QWidget,
                                                options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
            # Create readable widget name
            widget_name = child.__class__.__name__
            object_name = child.objectName()
            if object_name:
                display_name = f"{widget_name} ({object_name})"
            else:
                display_name = widget_name

            item = QtWidgets.QTreeWidgetItem(parent_item, [display_name])
            self.widget_map[id(item)] = child
            self.add_widgets(child, item)

    def on_item_clicked(self, item):
        widget = self.widget_map.get(id(item))
        if widget:
            self.element_selected.emit(widget)


class HotReloader(QtCore.QObject):
    reload_signal = QtCore.pyqtSignal()

    def __init__(self, module_path):
        super().__init__()
        self.module_path = module_path
        self.module = None
        self.main_window = None

        # Set up file watcher
        self.observer = Observer()
        self.event_handler = FileChangeHandler(self)
        self.observer.schedule(self.event_handler, str(Path(module_path).parent), recursive=False)
        self.observer.start()

        # Connect reload signal
        self.reload_signal.connect(self.reload_ui)

        # Initial load
        self.load_module()
        self.create_window()

    def load_module(self):
        try:
            # Remove module and its dependencies from cache
            module_name = Path(self.module_path).stem
            to_remove = [name for name in sys.modules if name.startswith(module_name)]
            for name in to_remove:
                del sys.modules[name]

            # Import module
            spec = importlib.util.spec_from_file_location(module_name, self.module_path)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
            return True
        except Exception as e:
            print(f"Error loading module: {e}")
            return False

    def create_window(self):
        if self.load_module():
            self.main_window = self.module.MainWindow()
            self.main_window.show()

    def reload_ui(self):
        try:
            # Store current window geometry
            old_geometry = None
            if self.main_window:
                old_geometry = self.main_window.geometry()
                self.main_window.close()
                self.main_window.deleteLater()

            # Create new window
            if self.load_module():
                self.main_window = self.module.MainWindow()

                # Restore geometry
                if old_geometry:
                    self.main_window.setGeometry(old_geometry)

                self.main_window.show()
                print("UI reloaded successfully")
        except Exception as e:
            print(f"Error reloading UI: {e}")
            import traceback
            traceback.print_exc()


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, reloader):
        self.reloader = reloader
        self.last_reload_time = 0
        self.reload_delay = 0.5  # Seconds

    def on_modified(self, event):
        current_time = time.time()
        if (event.src_path == str(Path(self.reloader.module_path).absolute()) and
                current_time - self.last_reload_time > self.reload_delay):
            self.last_reload_time = current_time
            print(f"Detected change in {event.src_path}, reloading...")
            self.reloader.reload_signal.emit()


def start_hot_reload(python_file):
    app = QtWidgets.QApplication(sys.argv)
    reloader = HotReloader(python_file)
    return app.exec()


def main():
    from .venv_utils import setup_environment, install_dependencies_in_venv
    if len(sys.argv) != 2:
        print("Usage: pyqt-hot-reload <path_to_ui_file.py>")
        sys.exit(1)

    ui_file = Path(sys.argv[1])
    if not ui_file.exists():
        print(f"Error: UI file '{ui_file}' not found")
        sys.exit(1)

    # Setup virtual environment
    python_path = setup_environment(ui_file.parent)
    if not python_path:
        sys.exit(1)

    # Check and install dependencies in venv if needed
    missing_packages = check_dependencies()
    if missing_packages:
        print("Installing missing dependencies in virtual environment...")
        if not install_dependencies_in_venv(python_path, missing_packages):
            print("Failed to install dependencies")
            sys.exit(1)

    # Start the hot reload
    start_hot_reload(str(ui_file))
