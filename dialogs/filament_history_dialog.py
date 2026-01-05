"""
Dialog displaying print history for a specific filament.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QMessageBox, QPushButton
)
from PyQt5.QtCore import Qt
from datetime import datetime

from utils.db_handler import get_filament_by_id, get_filament_history, delete_print
from utils.translations import t


class FilamentHistoryDialog(QDialog):
    """Dialog displaying print history for a specific filament."""

    def __init__(self, filament_id: str, parent=None):
        super().__init__(parent)
        self.filament_id = filament_id
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        filament = get_filament_by_id(self.filament_id)
        if not filament:
            QMessageBox.critical(self, t("error"), t("filament_not_found"))
            self.reject()
            return

        filament_type = filament.get('type', '')
        title_type = f" - {filament_type}" if filament_type else ""
        self.setWindowTitle(t("history_title").format(brand=f"{filament['brand']}{title_type}"))
        self.setModal(True)
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Filament info header
        spool_weight = filament.get('spool_weight', 0)
        spool_info = f"<br><b>{t('spool_weight_info_label')}</b> {spool_weight} g" if spool_weight > 0 else ""
        type_info = f" - {filament_type}" if filament_type else ""
        info_text = (
            f"<b>{t('filament_info')}</b> {filament['brand']}{type_info}<br>"
            f"<b>{t('color_info')}</b> <span style='background-color: {filament['color']}; "
            f"padding: 2px 8px; border-radius: 3px;'>{filament['color']}</span><br>"
            f"<b>{t('initial_weight_info')}</b> {filament['initial_weight']} g{spool_info}<br>"
            f"<b>{t('current_weight_info')}</b> {filament['current_weight']} g"
        )
        info_label = QLabel(info_text)
        info_label.setStyleSheet("padding: 10px; background-color: #1e1e1e; border-radius: 5px;")
        layout.addWidget(info_label)

        # History table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self._update_table_headers()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Apply dark styling to table
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

        layout.addWidget(self.table)

        # Buttons row
        buttons_layout = QHBoxLayout()
        
        self.delete_button = QPushButton(t("delete_print_btn"))
        self.delete_button.setFixedHeight(36)
        self.delete_button.clicked.connect(self.delete_selected_print)
        buttons_layout.addWidget(self.delete_button)
        
        buttons_layout.addStretch()
        
        self.close_button = QPushButton(t("close"))
        self.close_button.setFixedHeight(36)
        self.close_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)

        self.load_history()

    def _update_table_headers(self):
        """Update table headers with translated text."""
        headers = [t("date"), t("print_name"), t("weight_used")]
        for i, header_text in enumerate(headers):
            header_item = QTableWidgetItem(header_text)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(i, header_item)

    def load_history(self):
        """Load and display print history."""
        self.history_data = get_filament_history(self.filament_id)
        self.table.setRowCount(len(self.history_data))

        for row, print_record in enumerate(self.history_data):
            timestamp = datetime.fromisoformat(print_record['timestamp'])
            date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, date_item)

            name_item = QTableWidgetItem(print_record['print_name'])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 1, name_item)

            weight_item = QTableWidgetItem(str(print_record['weight_used']))
            weight_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            weight_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, weight_item)

        self.table.resizeRowsToContents()

    def delete_selected_print(self):
        """Delete the selected print record and restore weight to filament."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, t("error"), t("select_print_to_delete"))
            return
        
        row = selected_rows[0].row()
        
        if row >= len(self.history_data):
            return
        
        print_record = self.history_data[row]
        print_id = print_record.get("id")
        weight_used = print_record.get("weight_used", 0)
        print_name = print_record.get("print_name", "N/A")
        
        # Confirm deletion
        msg = f"{t('confirm_delete_print')}\n\n"
        msg += f"{t('print_name')}: {print_name}\n"
        msg += f"\n{t('weight_will_be_restored').format(weight=weight_used)}"
        
        reply = QMessageBox.question(
            self,
            t("confirm_delete"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if delete_print(print_id, restore_weight=True):
                QMessageBox.information(self, t("success"), t("print_deleted"))
                self.load_history()
                # Update filament info
                self._refresh_filament_info()
            else:
                QMessageBox.warning(self, t("error"), t("delete_failed"))

    def _refresh_filament_info(self):
        """Refresh the filament info label after weight change."""
        filament = get_filament_by_id(self.filament_id)
        if filament:
            spool_weight = filament.get('spool_weight', 0)
            spool_info = f"<br><b>{t('spool_weight_info_label')}</b> {spool_weight} g" if spool_weight > 0 else ""
            filament_type = filament.get('type', '')
            type_info = f" - {filament_type}" if filament_type else ""
            info_text = (
                f"<b>{t('filament_info')}</b> {filament['brand']}{type_info}<br>"
                f"<b>{t('color_info')}</b> <span style='background-color: {filament['color']}; "
                f"padding: 2px 8px; border-radius: 3px;'>{filament['color']}</span><br>"
                f"<b>{t('initial_weight_info')}</b> {filament['initial_weight']} g{spool_info}<br>"
                f"<b>{t('current_weight_info')}</b> {filament['current_weight']} g"
            )
            # Find and update the info label
            layout = self.layout()
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QLabel) and t('filament_info') in widget.text():
                    widget.setText(info_text)
                    break
