"""
Dialog for selecting filaments for multicolor prints.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from typing import List, Dict, Optional

from utils.db_handler import load_filaments, get_filament_by_id
from utils.translations import t, register_language_callback


def create_color_icon(color_hex: str, size: int = 16):
    """Create a square color icon from hex color."""
    from PyQt5.QtGui import QIcon, QPixmap, QColor
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color_hex))
    return QIcon(pixmap)


class MulticolorFilamentDialog(QDialog):
    """Dialog for selecting filaments for each weight in multicolor print."""

    def __init__(self, weights: List[float], parent=None):
        super().__init__(parent)
        self.weights = weights
        self.selected_filaments = []
        self.combos = []
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle(t("select_filaments_multicolor"))
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Info label
        info_label = QLabel(t("multicolor_info").format(count=len(self.weights)))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Form layout for filament selections
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        filaments = load_filaments()
        
        for i, weight in enumerate(self.weights):
            label = QLabel(t("filament_weight_label").format(num=i+1, weight=f"{weight:.2f}"))
            combo = QComboBox()
            combo.setMinimumWidth(300)
            combo.view().setMinimumWidth(350)
            
            # Add "Select filament" option
            combo.addItem(t("select_filament"), None)
            
            # Add available filaments
            for filament in filaments:
                filament_type = filament.get('type', '')
                if filament_type:
                    display_text = f"{filament['brand']} - {filament_type} ({filament['current_weight']}g)"
                else:
                    display_text = f"{filament['brand']} ({filament['current_weight']}g)"
                
                color_icon = create_color_icon(filament['color'])
                combo.addItem(color_icon, display_text, filament['id'])
            
            form_layout.addRow(label, combo)
            self.combos.append(combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton(t("cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        ok_button = QPushButton(t("ok"))
        ok_button.clicked.connect(self.accept_selection)
        buttons_layout.addWidget(ok_button)
        
        layout.addLayout(buttons_layout)

    def accept_selection(self):
        """Validate and accept the selection."""
        self.selected_filaments = []
        
        for i, combo in enumerate(self.combos):
            filament_id = combo.currentData()
            if not filament_id:
                QMessageBox.warning(
                    self, t("validation_error"),
                    t("select_filament_for_weight").format(num=i+1)
                )
                return
            
            filament = get_filament_by_id(filament_id)
            if not filament:
                QMessageBox.warning(self, t("error"), t("filament_not_found"))
                return
            
            # Check if enough weight available
            if filament['current_weight'] < self.weights[i]:
                QMessageBox.warning(
                    self, t("insufficient_filament"),
                    t("not_enough_filament_for_weight").format(
                        num=i+1, weight=f"{self.weights[i]:.2f}",
                        available=filament['current_weight'],
                        brand=filament['brand']
                    )
                )
                return
            
            self.selected_filaments.append({
                'filament_id': filament_id,
                'weight': self.weights[i],
                'filament': filament
            })
        
        self.accept()

    def get_selected_filaments(self) -> List[Dict]:
        """Get list of selected filaments with weights."""
        return self.selected_filaments

    def update_translations(self):
        """Update all UI text after language change."""
        self.setWindowTitle(t("select_filaments_multicolor"))
        # Note: Form labels would need to be updated, but they're created dynamically
        # This is acceptable as the dialog is typically shown once per file load



