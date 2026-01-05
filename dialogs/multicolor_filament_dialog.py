"""
Dialog for selecting filaments for multicolor prints.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFormLayout, QMessageBox, QGroupBox
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

    def __init__(self, file_data_list: List[Dict], parent=None):
        """
        Initialize dialog with file data.
        
        Args:
            file_data_list: List of dicts with 'filename' and 'weights' keys
                Example: [{'filename': 'file1.gcode', 'weights': [65.85, 117.50]}, ...]
        """
        super().__init__(parent)
        self.file_data_list = file_data_list
        self.selected_filaments = []
        self.file_filament_mapping = {}  # Dict mapping filename -> list of filament selections
        self.combos = []  # List of lists: one list per file, containing combos for each weight
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle(t("select_filaments_multicolor"))
        self.setModal(True)
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Info label
        total_weights = sum(len(fd['weights']) for fd in self.file_data_list)
        info_label = QLabel(t("multicolor_info").format(count=total_weights))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        filaments = load_filaments()
        
        # Create group for each file
        for file_data in self.file_data_list:
            filename = file_data['filename']
            weights = file_data['weights']
            
            # Group box for this file
            file_group = QGroupBox(filename)
            file_group.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #3a3a3a;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 12px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 8px;
                }
            """)
            file_layout = QVBoxLayout(file_group)
            file_layout.setSpacing(10)
            file_layout.setContentsMargins(16, 20, 16, 16)
            
            # Form layout for this file's weights
            form_layout = QFormLayout()
            form_layout.setSpacing(10)
            
            file_combos = []  # Combos for this file
            
            for i, weight in enumerate(weights):
                if len(weights) > 1:
                    label_text = t("filament_weight_label").format(num=i+1, weight=f"{weight:.2f}")
                else:
                    label_text = t("filament_weight_label_single").format(weight=f"{weight:.2f}")
                
                label = QLabel(label_text)
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
                file_combos.append(combo)
            
            file_layout.addLayout(form_layout)
            layout.addWidget(file_group)
            self.combos.append(file_combos)
        
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
        self.file_filament_mapping = {}  # Dict mapping filename -> list of filament selections
        
        weight_index = 0  # Global index across all files
        
        for file_idx, file_data in enumerate(self.file_data_list):
            filename = file_data['filename']
            weights = file_data['weights']
            file_combos = self.combos[file_idx]
            file_filaments = []  # Filaments for this specific file
            
            for weight_idx, (weight, combo) in enumerate(zip(weights, file_combos)):
                filament_id = combo.currentData()
                if not filament_id:
                    if len(weights) > 1:
                        error_msg = t("select_filament_for_file_weight").format(
                            file=filename, num=weight_idx+1
                        )
                    else:
                        error_msg = t("select_filament_for_file").format(file=filename)
                    QMessageBox.warning(self, t("validation_error"), error_msg)
                    return
                
                filament = get_filament_by_id(filament_id)
                if not filament:
                    QMessageBox.warning(self, t("error"), t("filament_not_found"))
                    return
                
                # Check if enough weight available
                if filament['current_weight'] < weight:
                    if len(weights) > 1:
                        error_msg = t("not_enough_filament_for_weight").format(
                            num=weight_idx+1,
                            weight=f"{weight:.2f}",
                            available=filament['current_weight'],
                            brand=filament['brand']
                        )
                    else:
                        error_msg = t("not_enough_filament_for_weight_single").format(
                            weight=f"{weight:.2f}",
                            available=filament['current_weight'],
                            brand=filament['brand']
                        )
                    QMessageBox.warning(self, t("insufficient_filament"), error_msg)
                    return
                
                filament_item = {
                    'filament_id': filament_id,
                    'weight': weight,
                    'filament': filament
                }
                self.selected_filaments.append(filament_item)
                file_filaments.append(filament_item)  # Add to file-specific list
                weight_index += 1
            
            # Store mapping for this file
            self.file_filament_mapping[filename] = file_filaments
        
        self.accept()

    def get_selected_filaments(self) -> List[Dict]:
        """Get list of selected filaments with weights."""
        return self.selected_filaments
    
    def get_selected_filaments_with_files(self) -> Dict:
        """Get selected filaments with file mapping."""
        return {
            'all_filaments': self.selected_filaments,
            'file_mapping': self.file_filament_mapping
        }

    def update_translations(self):
        """Update all UI text after language change."""
        self.setWindowTitle(t("select_filaments_multicolor"))
        # Note: Form labels would need to be updated, but they're created dynamically
        # This is acceptable as the dialog is typically shown once per file load



