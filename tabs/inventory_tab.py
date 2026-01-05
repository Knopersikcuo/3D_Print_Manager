"""
Inventory tab for managing filament stock.
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from utils.db_handler import load_filaments, get_filament_by_id, delete_filament
from utils.translations import t, register_language_callback
from dialogs.add_filament_dialog import AddFilamentDialog
from dialogs.edit_filament_dialog import EditFilamentDialog
from dialogs.brands_dialog import BrandsDialog
from dialogs.filament_history_dialog import FilamentHistoryDialog


class InventoryTab(QWidget):
    """Inventory tab for managing filaments."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the inventory tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.add_filament_btn = QPushButton(t("add_filament"))
        self.add_filament_btn.clicked.connect(self.show_add_filament_dialog)
        buttons_layout.addWidget(self.add_filament_btn)

        self.edit_filament_btn = QPushButton(t("edit"))
        self.edit_filament_btn.clicked.connect(self.show_edit_filament_dialog)
        self.edit_filament_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_filament_btn)

        self.delete_filament_btn = QPushButton(t("delete"))
        self.delete_filament_btn.clicked.connect(self.delete_selected_filament)
        self.delete_filament_btn.setEnabled(False)
        self.delete_filament_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f87171, stop:1 #ef4444);
            }
        """)
        buttons_layout.addWidget(self.delete_filament_btn)

        self.show_history_btn = QPushButton(t("filament_history"))
        self.show_history_btn.clicked.connect(self.show_filament_history)
        self.show_history_btn.setEnabled(False)
        buttons_layout.addWidget(self.show_history_btn)

        self.brands_btn = QPushButton(t("brands"))
        self.brands_btn.clicked.connect(self.show_brands_dialog)
        buttons_layout.addWidget(self.brands_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self._update_table_headers()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 100)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Apply consistent dark styling to table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #1e1e1e;
                gridline-color: #333;
                color: #e0e0e0;
            }
            QTableWidget::item {
                background-color: #1e1e1e;
                color: #e0e0e0;
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #7c3aed;
                color: white;
            }
        """)

        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)

        layout.addWidget(self.table)

        self.refresh_table()

    def _update_table_headers(self):
        """Update table headers with translated text."""
        headers = [t("color"), t("brand"), t("initial_weight"), t("current_weight")]
        for i, header_text in enumerate(headers):
            header_item = QTableWidgetItem(header_text)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(i, header_item)

    def refresh_table(self):
        """Refresh the filament table with current data."""
        filaments = load_filaments()
        self.table.setRowCount(len(filaments))

        for row, filament in enumerate(filaments):
            # Color column
            color_str = filament['color']
            if not color_str.startswith('#'):
                color_str = '#' + color_str
            color = QColor(color_str)
            if not color.isValid():
                color = QColor("#000000")

            color_label = QLabel("")
            color_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color_str};
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }}
            """)
            color_label.setProperty("filament_id", filament['id'])
            self.table.setCellWidget(row, 0, color_label)

            # Brand column
            filament_type = filament.get('type', '')
            if filament_type:
                brand_text = f"{filament['brand']} - {filament_type}"
            else:
                brand_text = filament['brand']
            brand_item = QTableWidgetItem(brand_text)
            brand_item.setData(Qt.UserRole, filament['id'])
            brand_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            brand_item.setTextAlignment(Qt.AlignCenter)
            font = brand_item.font()
            font.setPointSize(12)
            font.setBold(True)
            brand_item.setFont(font)
            self.table.setItem(row, 1, brand_item)

            # Initial weight column
            initial_weight_item = QTableWidgetItem(f"{filament['initial_weight']} g")
            initial_weight_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            initial_weight_item.setTextAlignment(Qt.AlignCenter)
            font = initial_weight_item.font()
            font.setPointSize(12)
            initial_weight_item.setFont(font)
            self.table.setItem(row, 2, initial_weight_item)

            # Current weight column
            current_weight_item = QTableWidgetItem(f"{filament['current_weight']} g")
            current_weight_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            current_weight_item.setTextAlignment(Qt.AlignCenter)
            font = current_weight_item.font()
            font.setPointSize(12)
            if filament['current_weight'] < filament['initial_weight']:
                font.setBold(True)
            current_weight_item.setFont(font)
            self.table.setItem(row, 3, current_weight_item)

        self.table.resizeRowsToContents()

    def on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.table.selectedItems()) > 0
        self.show_history_btn.setEnabled(has_selection)
        self.edit_filament_btn.setEnabled(has_selection)
        self.delete_filament_btn.setEnabled(has_selection)

    def on_item_double_clicked(self, item):
        """Handle double-click on table item."""
        self.show_filament_history()

    def get_selected_filament_id(self) -> Optional[str]:
        """Get the ID of the currently selected filament."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return None

        row = selected_items[0].row()
        brand_item = self.table.item(row, 1)
        if brand_item:
            return brand_item.data(Qt.UserRole)
        return None

    def show_add_filament_dialog(self):
        """Show dialog for adding a new filament."""
        dialog = AddFilamentDialog(self)
        if dialog.exec_() == 1:  # QDialog.Accepted
            self.refresh_table()

    def show_edit_filament_dialog(self):
        """Show dialog for editing selected filament."""
        filament_id = self.get_selected_filament_id()
        if filament_id:
            dialog = EditFilamentDialog(filament_id, self)
            if dialog.exec_() == 1:  # QDialog.Accepted
                self.refresh_table()

    def show_brands_dialog(self):
        """Show dialog for managing brands."""
        dialog = BrandsDialog(self)
        dialog.exec_()

    def show_filament_history(self):
        """Show history dialog for selected filament."""
        filament_id = self.get_selected_filament_id()
        if filament_id:
            dialog = FilamentHistoryDialog(filament_id, self)
            dialog.exec_()

    def delete_selected_filament(self):
        """Delete selected filament after confirmation."""
        filament_id = self.get_selected_filament_id()
        if not filament_id:
            return

        filament = get_filament_by_id(filament_id)
        if not filament:
            QMessageBox.warning(self, t("error"), t("filament_not_found"))
            return

        reply = QMessageBox.question(
            self, t("confirm_delete"),
            f"{t('confirm_delete_filament')}\n"
            f"{t('brand')}: {filament['brand']}\n"
            f"{t('filament_type')}: {filament.get('type', 'N/A')}\n"
            f"{t('color')}: {filament['color']}\n\n"
            f"{t('irreversible')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if delete_filament(filament_id):
                    QMessageBox.information(self, t("success"), t("filament_deleted"))
                    self.refresh_table()
                else:
                    QMessageBox.warning(self, t("error"), t("delete_failed"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), f"{t('error')}: {str(e)}")

    def update_translations(self):
        """Update all UI text after language change."""
        self.add_filament_btn.setText(t("add_filament"))
        self.edit_filament_btn.setText(t("edit"))
        self.delete_filament_btn.setText(t("delete"))
        self.show_history_btn.setText(t("filament_history"))
        self.brands_btn.setText(t("brands"))
        self._update_table_headers()
