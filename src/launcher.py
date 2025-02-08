import sys
from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLineEdit, QFileDialog,
                             QLabel, QMessageBox, QSplitter)

from src.hot_reload import HotReloader, ElementTree
from src.utils import check_dependencies
from src.venv_utils import setup_environment, install_dependencies_in_venv


class PropertyEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_widget = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Add header label
        self.header_label = QtWidgets.QLabel("Properties")
        self.header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                padding: 8px;
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
        """)
        layout.addWidget(self.header_label)

        # Selected widget info
        self.widget_info = QtWidgets.QLabel("No widget selected")
        self.widget_info.setStyleSheet("""
            QLabel {
                color: #666;
                padding: 4px 8px;
                font-style: italic;
            }
        """)
        layout.addWidget(self.widget_info)

        # Property table
        self.property_table = QtWidgets.QTableWidget()
        self.property_table.setColumnCount(2)
        self.property_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.property_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.property_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.property_table.verticalHeader().setVisible(False)
        self.property_table.setAlternatingRowColors(True)
        layout.addWidget(self.property_table)

        # Apply button
        self.apply_button = QtWidgets.QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)

        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 2px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 2px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e8f0fe;
                color: #000;
            }
            QTableWidget::item:focus {
                background-color: #e8f0fe;
                color: #000;
                border: 1px solid #4a90e2;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
                color: #333;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                margin: 8px;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
            QPushButton:hover:!disabled {
                background-color: #357abd;
            }
        """)

        # Connect table signals
        self.property_table.itemChanged.connect(self.on_property_changed)
        self.property_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked |
            QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )

    def on_property_changed(self, item):
        if item.column() == 1:  # Only enable button when values are changed
            self.apply_button.setEnabled(True)

    def update_properties(self, widget):
        self.current_widget = widget
        self.property_table.setRowCount(0)
        self.apply_button.setEnabled(False)

        if not widget:
            self.widget_info.setText("No widget selected")
            return

        # Update widget info
        self.widget_info.setText(f"Selected: {widget.__class__.__name__} ({widget.objectName() or 'Unnamed'})")

        # Get widget properties
        properties = {
            "objectName": (widget.objectName(), "str"),
            "geometry": (f"x:{widget.x()}, y:{widget.y()}, w:{widget.width()}, h:{widget.height()}", "geometry"),
            "visible": (widget.isVisible(), "bool"),
            "enabled": (widget.isEnabled(), "bool"),
            "styleSheet": (widget.styleSheet(), "str"),
        }

        # Add specific properties based on widget type
        if isinstance(widget, QtWidgets.QLabel):
            properties.update({
                "text": (widget.text(), "str"),
                "alignment": (str(widget.alignment()), "alignment"),
            })
        elif isinstance(widget, QtWidgets.QPushButton):
            properties.update({
                "text": (widget.text(), "str"),
            })
        elif isinstance(widget, QtWidgets.QLineEdit):
            properties.update({
                "text": (widget.text(), "str"),
                "placeholderText": (widget.placeholderText(), "str"),
            })

        # Populate table
        for prop_name, (value, prop_type) in properties.items():
            row = self.property_table.rowCount()
            self.property_table.insertRow(row)

            # Property name
            name_item = QtWidgets.QTableWidgetItem(prop_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make name non-editable
            name_item.setToolTip(f"Type: {prop_type}")
            self.property_table.setItem(row, 0, name_item)

            # Property value
            value_item = QtWidgets.QTableWidgetItem(str(value))
            value_item.setData(Qt.ItemDataRole.UserRole, prop_type)  # Store property type
            self.property_table.setItem(row, 1, value_item)

    def apply_changes(self):
        if not self.current_widget:
            return

        for row in range(self.property_table.rowCount()):
            prop_name = self.property_table.item(row, 0).text()
            value = self.property_table.item(row, 1).text()
            prop_type = self.property_table.item(row, 1).data(Qt.ItemDataRole.UserRole)

            try:
                if prop_name == "geometry":
                    # Parse geometry string (x:10, y:20, w:100, h:30)
                    geo_dict = dict(item.split(':') for item in value.replace(' ', '').split(','))
                    self.current_widget.setGeometry(
                        int(geo_dict['x']),
                        int(geo_dict['y']),
                        int(geo_dict['w']),
                        int(geo_dict['h'])
                    )
                elif prop_name == "styleSheet":
                    self.current_widget.setStyleSheet(value)
                elif prop_name == "text" and hasattr(self.current_widget, 'setText'):
                    self.current_widget.setText(value)
                elif prop_name == "enabled":
                    self.current_widget.setEnabled(value.lower() == "true")
                elif prop_name == "visible":
                    self.current_widget.setVisible(value.lower() == "true")
                elif prop_name == "objectName":
                    self.current_widget.setObjectName(value)
                elif prop_name == "placeholderText" and isinstance(self.current_widget, QtWidgets.QLineEdit):
                    self.current_widget.setPlaceholderText(value)

            except Exception as e:
                print(f"Error applying property {prop_name}: {e}")

        self.apply_button.setEnabled(False)

        # Update the tree to reflect any name changes
        if isinstance(self.parent(), LauncherWindow):
            self.parent().element_tree.populate_tree(self.parent().hot_reloader.main_window)


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hot_reloader = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("PyQt Hot Reload Launcher by Madhusudan")
        self.setMinimumSize(QSize(1000, 700))

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Top controls container
        top_controls = QWidget()
        top_controls_layout = QHBoxLayout(top_controls)
        top_controls_layout.setContentsMargins(0, 0, 0, 0)
        top_controls_layout.setSpacing(8)

        # File selection area
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select Python UI file...")
        self.path_input.setMinimumHeight(36)

        browse_button = QPushButton("Browse")
        browse_button.setMinimumHeight(36)
        browse_button.setMinimumWidth(80)
        browse_button.clicked.connect(self.browse_file)

        # Start/Stop button
        self.toggle_button = QPushButton("Start")
        self.toggle_button.setMinimumHeight(36)
        self.toggle_button.setMinimumWidth(80)
        self.toggle_button.clicked.connect(self.toggle_hot_reload)

        top_controls_layout.addWidget(self.path_input, stretch=1)
        top_controls_layout.addWidget(browse_button)
        top_controls_layout.addWidget(self.toggle_button)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 5px 0;
            }
        """)

        # Add top controls to main layout
        main_layout.addWidget(top_controls)
        main_layout.addWidget(self.status_label)

        # Create inspector area
        inspector_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Element Tree
        self.element_tree = ElementTree()
        inspector_splitter.addWidget(self.element_tree)

        # Property Editor
        self.property_editor = PropertyEditor()
        inspector_splitter.addWidget(self.property_editor)

        # Connect signals
        self.element_tree.element_selected.connect(self.property_editor.update_properties)

        # Set initial splitter sizes
        inspector_splitter.setSizes([400, 600])

        main_layout.addWidget(inspector_splitter, stretch=1)

        # Add footer container
        footer_container = QWidget()
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0, 8, 0, 0)

        # Add version label
        version_label = QLabel("Hot Reloader v1.0")
        version_label.setStyleSheet("""
                    QLabel {
                        color: #999;
                        font-size: 11px;
                        font-style: italic;
                    }
                """)

        # Add spacer to push version label to the right
        footer_layout.addStretch()
        footer_layout.addWidget(version_label)

        # Add footer to main layout
        main_layout.addWidget(footer_container)

        # Style the window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 2px 3px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2d6da3;
            }
            QPushButton#toggle_button_stop {
                background-color: #e74c3c;
            }
            QPushButton#toggle_button_stop:hover {
                background-color: #c0392b;
            }
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
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
            QSplitter::handle {
                background-color: #ddd;
                width: 1px;
                margin: 2px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: 500;
            }
        """)

    def toggle_hot_reload(self):
        if self.hot_reloader is None:
            self.start_hot_reload()
        else:
            self.stop_hot_reload()

    def start_hot_reload(self):
        file_path = self.path_input.text()
        if not file_path:
            QMessageBox.warning(self, "Error", "Please select a Python UI file")
            return

        if not Path(file_path).exists():
            QMessageBox.warning(self, "Error", "Selected file does not exist")
            return

        try:
            # Setup virtual environment
            python_path = setup_environment(Path(file_path).parent)
            if not python_path:
                QMessageBox.critical(self, "Error", "Failed to setup virtual environment")
                return

            # Check and install dependencies
            missing_packages = check_dependencies()
            if missing_packages:
                self.status_label.setText("Installing dependencies...")
                if not install_dependencies_in_venv(python_path, missing_packages):
                    QMessageBox.critical(self, "Error", "Failed to install dependencies")
                    return

            self.status_label.setText("Starting hot reload...")
            self.hot_reloader = HotReloader(file_path)

            # Update the element tree with the new window
            if self.hot_reloader.main_window:
                self.element_tree.populate_tree(self.hot_reloader.main_window)

            # Update UI state
            self.toggle_button.setText("Stop")
            self.toggle_button.setObjectName("toggle_button_stop")
            self.toggle_button.setStyleSheet("")  # Force style refresh
            self.status_label.setText("Hot reload active")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start hot reload: {str(e)}")
            self.status_label.setText("Error occurred")

    def stop_hot_reload(self):
        if self.hot_reloader:
            try:
                self.hot_reloader.observer.stop()
                self.hot_reloader.observer.join()
                if self.hot_reloader.main_window:
                    self.hot_reloader.main_window.close()
                self.hot_reloader = None

                # Clear the element tree
                self.element_tree.clear()
                self.property_editor.update_properties(None)

                # Update UI state
                self.toggle_button.setText("Start")
                self.toggle_button.setObjectName("")
                self.toggle_button.setStyleSheet("")  # Force style refresh
                self.status_label.setText("Hot reload stopped")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to stop hot reload: {str(e)}")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python UI File",
            "",
            "Python Files (*.py)"
        )
        if file_path:
            self.path_input.setText(file_path)

    def closeEvent(self, event):
        self.stop_hot_reload()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
