"""
Dialog for editing an existing print record.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QLineEdit, QDialogButtonBox, QMessageBox
)
from PyQt5.QtGui import QIcon, QPixmap, QColor

from utils.db_handler import get_print_by_id, update_print, load_filaments, get_filament_by_id
from utils.translations import t, format_currency, get_currency_symbol


def create_color_icon(color_hex: str, size: int = 16) -> QIcon:
    """Create a square color icon from hex color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color_hex))
    return QIcon(pixmap)


class EditPrintDialog(QDialog):
    """Dialog for editing an existing print record."""

    def __init__(self, print_id: str, parent=None):
        super().__init__(parent)
        self.print_id = print_id
        self.print_record = get_print_by_id(print_id)
        if not self.print_record:
            QMessageBox.critical(self, t("error"), "Print record not found.")
            self.reject()
            return

        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle(t("edit_print_title"))
        self.setModal(True)
        self.setMinimumSize(450, 300)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Print name
        name_layout = QHBoxLayout()
        name_label = QLabel(t("print_name") + ":")
        name_layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setText(self.print_record.get('print_name', ''))
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Filament selection
        filament_layout = QHBoxLayout()
        filament_label = QLabel(t("filament") + ":")
        filament_layout.addWidget(filament_label)
        self.filament_combo = QComboBox()
        self._populate_filaments()
        current_filament_id = self.print_record.get('filament_id')
        if current_filament_id:
            for i in range(self.filament_combo.count()):
                if self.filament_combo.itemData(i) == current_filament_id:
                    self.filament_combo.setCurrentIndex(i)
                    break
        self.filament_combo.currentIndexChanged.connect(self.update_available_weight)
        filament_layout.addWidget(self.filament_combo)
        layout.addLayout(filament_layout)

        # Available weight info
        self.available_weight_label = QLabel()
        self.update_available_weight()
        layout.addWidget(self.available_weight_label)

        # Weight used
        weight_layout = QHBoxLayout()
        weight_label = QLabel(t("weight_used") + ":")
        weight_layout.addWidget(weight_label)
        self.weight_input = QSpinBox()
        self.weight_input.setRange(1, 10000)
        self.weight_input.setValue(self.print_record.get('weight_used', 0))
        self.weight_input.setSuffix(" g")
        self.weight_input.valueChanged.connect(self.update_price_preview)
        weight_layout.addWidget(self.weight_input)
        layout.addLayout(weight_layout)

        # Price
        price_layout = QHBoxLayout()
        price_label = QLabel(t("price") + ":")
        price_layout.addWidget(price_label)
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 100000)
        self.price_input.setDecimals(2)
        price_value = self.print_record.get('price')
        if price_value is not None:
            self.price_input.setValue(price_value)
        self.price_input.setSuffix(f" {get_currency_symbol()}")
        self.price_input.valueChanged.connect(self.update_price_preview)
        price_layout.addWidget(self.price_input)
        layout.addLayout(price_layout)

        # Price preview (converted to current currency)
        self.price_preview_label = QLabel()
        self.update_price_preview()
        layout.addWidget(self.price_preview_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_dialog)
        button_box.rejected.connect(self.reject)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(t("save_changes"))
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        cancel_btn.setText(t("cancel"))
        layout.addWidget(button_box)

    def _populate_filaments(self):
        """Populate filament combo box with available filaments."""
        filaments = load_filaments()
        self.filament_combo.clear()
        
        for filament in filaments:
            color_icon = create_color_icon(filament.get('color', '#888888'))
            filament_type = filament.get('type', '')
            if filament_type:
                display_text = f"{filament['brand']} - {filament_type}"
            else:
                display_text = filament['brand']
            self.filament_combo.addItem(color_icon, display_text, filament['id'])

    def update_available_weight(self):
        """Update available weight label."""
        filament_id = self.filament_combo.currentData()
        if filament_id:
            filament = get_filament_by_id(filament_id)
            if filament:
                available = filament['current_weight']
                old_weight = self.print_record.get('weight_used', 0)
                old_filament_id = self.print_record.get('filament_id')
                
                # If same filament, add back the old weight
                if old_filament_id == filament_id:
                    available += old_weight
                
                self.available_weight_label.setText(
                    f"{t('available_weight')}: {available} g"
                )
                self.available_weight_label.setStyleSheet("color: #22c55e;")
            else:
                self.available_weight_label.setText("")
        else:
            self.available_weight_label.setText("")

    def update_price_preview(self):
        """Update price preview label."""
        price = self.price_input.value()
        if price > 0:
            formatted = format_currency(price)
            self.price_preview_label.setText(f"{t('price')}: {formatted}")
            self.price_preview_label.setStyleSheet("color: #7c3aed; font-weight: 600;")
        else:
            self.price_preview_label.setText("")

    def accept_dialog(self):
        """Validate and accept the dialog."""
        print_name = self.name_input.text().strip()
        if not print_name:
            QMessageBox.warning(self, t("error"), f"{t('print_name')} is required.")
            return

        filament_id = self.filament_combo.currentData()
        if not filament_id:
            QMessageBox.warning(self, t("error"), f"{t('filament')} is required.")
            return

        weight_used = self.weight_input.value()
        if weight_used <= 0:
            QMessageBox.warning(self, t("error"), f"{t('weight_used')} must be greater than 0.")
            return

        # Check available weight
        filament = get_filament_by_id(filament_id)
        if not filament:
            QMessageBox.warning(self, t("error"), t("filament_not_found"))
            return

        available_weight = filament['current_weight']
        old_weight = self.print_record.get('weight_used', 0)
        old_filament_id = self.print_record.get('filament_id')
        
        # If same filament, add back the old weight
        if old_filament_id == filament_id:
            available_weight += old_weight

        if available_weight < weight_used:
            QMessageBox.warning(
                self, t("error"),
                t("not_enough_filament").format(weight=available_weight)
            )
            return

        price = self.price_input.value()
        if price <= 0:
            price = None

        try:
            update_print(
                print_id=self.print_id,
                print_name=print_name,
                filament_id=filament_id,
                weight_used=weight_used,
                price=price
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"Failed to update print:\n{str(e)}")

