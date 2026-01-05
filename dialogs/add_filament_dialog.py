"""
Dialog for adding a new filament.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QDialogButtonBox, QMessageBox
)
from PyQt5.QtGui import QColor

from utils.db_handler import add_filament, get_all_brands, get_spool_weight
from utils.translations import t


class AddFilamentDialog(QDialog):
    """Dialog for adding a new filament."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_color = QColor("#FF0000")
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle(t("add_filament_title"))
        self.setModal(True)
        self.setMinimumSize(400, 350)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Color selection
        color_layout = QHBoxLayout()
        self.color_label_title = QLabel(t("color_label"))
        color_layout.addWidget(self.color_label_title)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(50, 30)
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color.name()};")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        self.color_label = QLabel(self.selected_color.name())
        color_layout.addWidget(self.color_label)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        # Brand selection
        brand_layout = QHBoxLayout()
        self.brand_label_title = QLabel(t("brand_label"))
        brand_layout.addWidget(self.brand_label_title)
        self.brand_combo = QComboBox()
        brands = get_all_brands()
        self.brand_combo.addItems(brands)
        self.brand_combo.currentTextChanged.connect(self.on_brand_changed)
        brand_layout.addWidget(self.brand_combo)
        layout.addLayout(brand_layout)

        # Filament type selection
        type_layout = QHBoxLayout()
        self.type_label_title = QLabel(t("filament_type"))
        type_layout.addWidget(self.type_label_title)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["PLA", "PETG", "ABS", "ASA", "PP", "TPU", "NYLON", "PA", "PC"])
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Checkbox for weight without spool
        self.without_spool_checkbox = QCheckBox(t("without_spool"))
        self.without_spool_checkbox.stateChanged.connect(self.on_spool_checkbox_changed)
        layout.addWidget(self.without_spool_checkbox)

        # Spool weight info
        self.spool_info_label = QLabel()
        layout.addWidget(self.spool_info_label)

        # Weight input
        weight_layout = QHBoxLayout()
        self.weight_label = QLabel(t("weight_with_spool"))
        weight_layout.addWidget(self.weight_label)
        self.weight_input = QSpinBox()
        self.weight_input.setRange(1, 10000)
        self.weight_input.setValue(1000)
        self.weight_input.valueChanged.connect(self.update_net_weight)
        weight_layout.addWidget(self.weight_input)
        layout.addLayout(weight_layout)

        # Net weight info
        self.net_weight_label = QLabel()
        layout.addWidget(self.net_weight_label)

        # Initialize display
        if self.brand_combo.count() > 0:
            self.on_brand_changed(self.brand_combo.currentText())

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_dialog)
        button_box.rejected.connect(self.reject)
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        cancel_btn.setText(t("cancel"))
        layout.addWidget(button_box)

    def choose_color(self):
        """Open color picker dialog."""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.selected_color, self, t("select_color"))
        if color.isValid():
            self.selected_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.color_label.setText(color.name())

    def on_spool_checkbox_changed(self, state):
        """Handle checkbox state change."""
        self.update_net_weight()
        self.update_weight_label()

    def update_weight_label(self):
        """Update weight label text based on checkbox state."""
        if self.without_spool_checkbox.isChecked():
            self.weight_label.setText(t("weight_without_spool"))
        else:
            self.weight_label.setText(t("weight_with_spool"))

    def on_brand_changed(self, brand: str):
        """Handle brand selection change."""
        spool_weight = get_spool_weight(brand)
        if self.without_spool_checkbox.isChecked():
            self.spool_info_label.setText(
                t("spool_weight_info_no_sub").format(brand=brand, weight=spool_weight)
            )
        else:
            self.spool_info_label.setText(
                t("spool_weight_info").format(brand=brand, weight=spool_weight)
            )
        self.update_net_weight()

    def update_net_weight(self):
        """Update net weight display."""
        brand = self.brand_combo.currentText()
        spool_weight = get_spool_weight(brand)
        total_weight = self.weight_input.value()

        if self.without_spool_checkbox.isChecked():
            net_weight = total_weight
            self.net_weight_label.setText(
                t("net_weight_display_no_spool").format(weight=net_weight)
            )
        else:
            net_weight = total_weight - spool_weight
            if net_weight > 0:
                self.net_weight_label.setText(
                    t("net_weight_display").format(weight=net_weight)
                )
            else:
                self.net_weight_label.setText(
                    t("net_weight_warning").format(weight=net_weight)
                )

    def accept_dialog(self):
        """Validate and accept the dialog."""
        brand = self.brand_combo.currentText()
        if not brand:
            QMessageBox.warning(self, t("error"), t("brand_required"))
            return

        total_weight = self.weight_input.value()
        without_spool = self.without_spool_checkbox.isChecked()

        if not without_spool:
            spool_weight = get_spool_weight(brand)
            net_weight = total_weight - spool_weight
            if net_weight <= 0:
                QMessageBox.warning(
                    self, t("error"),
                    t("weight_too_small").format(
                        total=total_weight, brand=brand, spool=spool_weight, net=net_weight
                    )
                )
                return

        filament_type = self.type_combo.currentText()

        try:
            add_filament(
                color=self.selected_color.name(),
                brand=brand,
                filament_type=filament_type,
                initial_weight=total_weight,
                without_spool=without_spool
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, t("error"), t("add_filament_error").format(error=str(e)))
