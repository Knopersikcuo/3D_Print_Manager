"""
Calculator tab for price calculation with filament selection from inventory.
"""

import os
from typing import Optional, Dict, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QComboBox, QFormLayout, QMessageBox, QFileDialog,
    QSpinBox, QSizePolicy, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor, QBrush, QPixmap, QIcon, QPainter

from utils.db_handler import load_filaments, get_filament_by_id, add_print
from utils.gcode_parser import GCodeParser
from utils.price_calculator import PriceCalculator
from utils.translations import t, register_language_callback, format_currency, register_currency_callback
from dialogs.multicolor_filament_dialog import MulticolorFilamentDialog


class DragDropListWidget(QListWidget):
    """List widget with drag and drop support for G-code files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            gcode_files = [url for url in urls if url.toLocalFile().lower().endswith(
                ('.gcode', '.gco', '.nc', '.bgcode')
            )]
            if gcode_files:
                event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.gcode', '.gco', '.nc', '.bgcode')):
                    if not any(self.item(i).data(Qt.UserRole) == file_path
                             for i in range(self.count())):
                        item = QListWidgetItem(os.path.basename(file_path))
                        item.setData(Qt.UserRole, file_path)
                        self.addItem(item)
            event.acceptProposedAction()


def create_color_icon(color_str: str, size: int = 20) -> QIcon:
    """Create a colored square icon for combo boxes."""
    if not color_str.startswith('#'):
        color_str = '#' + color_str
    color = QColor(color_str)
    if not color.isValid():
        color = QColor("#000000")

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(color))
    painter.setPen(QColor(0, 0, 0, 0))
    margin = 2
    painter.drawRect(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.end()

    return QIcon(pixmap)


class CalculatorTab(QWidget):
    """Calculator tab with G-code import and filament selection from inventory."""

    def __init__(self, config: Dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_filament_id = None
        self.current_multicolor_filaments = []  # List of {filament_id, weight} for multicolor
        self.current_price_result = None
        self.init_ui()

    def _create_cost_row(self, label_widget: QLabel, value_widget: QLabel, accent_color: str) -> QWidget:
        """Create a styled cost row with label and value."""
        row = QWidget()
        row.setStyleSheet(f"""
            QWidget {{
                background-color: #1a1a2e;
                border-radius: 4px;
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 12, 0)
        row_layout.setSpacing(0)
        
        # Color accent bar
        accent_bar = QLabel()
        accent_bar.setFixedWidth(4)
        accent_bar.setStyleSheet(f"background-color: {accent_color}; border-radius: 0; border-top-left-radius: 4px; border-bottom-left-radius: 4px;")
        row_layout.addWidget(accent_bar)
        
        # Content container
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(10, 8, 0, 8)
        content_layout.setSpacing(8)
        
        label_widget.setStyleSheet("color: #a0a0a0; font-size: 12px; background: transparent;")
        value_widget.setStyleSheet(f"color: {accent_color}; font-size: 13px; font-weight: 600; background: transparent;")
        
        content_layout.addWidget(label_widget)
        content_layout.addStretch()
        content_layout.addWidget(value_widget)
        
        row_layout.addWidget(content, 1)
        
        return row

    def init_ui(self):
        """Initialize the calculator tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Three-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)

        # Left column - Input parameters
        left_column = QVBoxLayout()
        left_column.setSpacing(16)

        # Input form group
        self.input_group = QGroupBox(t("filament_selection"))
        self.input_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.input_group.setFixedWidth(320)
        self.input_group.setMinimumHeight(320)
        input_layout = QFormLayout()
        input_layout.setSpacing(14)
        input_layout.setContentsMargins(24, 24, 24, 24)
        input_layout.setLabelAlignment(Qt.AlignRight)
        self.input_group.setLayout(input_layout)

        # Filament selection from inventory
        self.filament_combo = QComboBox()
        self.filament_combo.currentIndexChanged.connect(self.on_filament_changed)
        # Make dropdown list wider to show full filament names
        self.filament_combo.view().setMinimumWidth(350)
        self.filament_label = QLabel("Filament:")
        input_layout.addRow(self.filament_label, self.filament_combo)

        # Available weight display (can show multicolor info)
        self.available_weight_label = QLabel(t("available_weight") + " - g")
        self.available_weight_label.setStyleSheet("color: #7c3aed; font-size: 12px; font-weight: 500;")
        self.available_weight_label.setWordWrap(True)
        self.available_weight_label.setMinimumHeight(40)
        input_layout.addRow("", self.available_weight_label)

        # Filament weight input (can be auto-filled from G-code)
        self.filament_weight_input = QLineEdit()
        self.filament_weight_input.setPlaceholderText(t("placeholder_weight"))
        self.weight_label = QLabel(t("filament_weight"))
        input_layout.addRow(self.weight_label, self.filament_weight_input)

        # Time input
        self.print_time_input = QLineEdit()
        self.print_time_input.setPlaceholderText(t("placeholder_time"))
        self.print_time_input.textChanged.connect(self.update_energy_consumption)
        self.time_label = QLabel(t("total_time"))
        input_layout.addRow(self.time_label, self.print_time_input)

        # Copies
        self.copies_input = QSpinBox()
        self.copies_input.setRange(1, 1000)
        self.copies_input.setValue(1)
        self.copies_label = QLabel(t("copies"))
        input_layout.addRow(self.copies_label, self.copies_input)

        # Energy consumption display
        self.energy_consumption_label = QLabel("-")
        self.energy_consumption_label.setStyleSheet("color: #7c3aed; font-size: 13px; font-weight: 500;")
        self.energy_label = QLabel(t("energy_cost"))
        input_layout.addRow(self.energy_label, self.energy_consumption_label)

        left_column.addWidget(self.input_group)

        # Advanced options
        self.advanced_group = QGroupBox(t("advanced"))
        self.advanced_group.setFixedWidth(320)
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QFormLayout()
        advanced_layout.setSpacing(14)
        advanced_layout.setContentsMargins(24, 24, 24, 24)
        advanced_layout.setLabelAlignment(Qt.AlignRight)

        self.postprocess_time_input = QLineEdit()
        self.postprocess_time_input.setPlaceholderText("0")
        self.postprocess_label = QLabel(t("postprocess_time"))
        advanced_layout.addRow(self.postprocess_label, self.postprocess_time_input)

        self.advanced_group.setLayout(advanced_layout)
        left_column.addWidget(self.advanced_group)

        # Buttons
        self.calculate_button = QPushButton(t("calculate"))
        self.calculate_button.setMinimumHeight(48)
        self.calculate_button.clicked.connect(self.calculate_price)
        left_column.addWidget(self.calculate_button)

        self.execute_button = QPushButton(t("execute_print"))
        self.execute_button.setMinimumHeight(48)
        self.execute_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.execute_button.clicked.connect(self.execute_print)
        left_column.addWidget(self.execute_button)
        columns_layout.addLayout(left_column, 0)

        # Middle column - G-code import
        middle_column = QVBoxLayout()
        middle_column.setSpacing(16)

        self.gcode_group = QGroupBox(t("gcode_files"))
        self.gcode_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gcode_group.setMinimumWidth(400)
        self.gcode_group.setMinimumHeight(550)
        gcode_layout = QVBoxLayout()
        gcode_layout.setSpacing(16)
        gcode_layout.setContentsMargins(24, 24, 24, 24)

        self.instructions_label = QLabel(t("drag_drop_hint"))
        self.instructions_label.setStyleSheet("color: #999; font-size: 12px; padding: 6px 0;")
        gcode_layout.addWidget(self.instructions_label)

        self.gcode_list = DragDropListWidget()
        self.gcode_list.setMinimumHeight(400)
        self.gcode_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 2px dashed #444;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QListWidget::item {
                color: #e0e0e0;
                padding: 6px 8px;
                border-bottom: 1px solid #333;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #7c3aed;
                color: white;
            }
        """)
        gcode_layout.addWidget(self.gcode_list)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.select_files_button = QPushButton(t("add_files"))
        self.select_files_button.setMinimumHeight(40)
        self.select_files_button.clicked.connect(self.select_gcode_files)
        buttons_layout.addWidget(self.select_files_button)

        self.clear_button = QPushButton(t("clear_all"))
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self.clear_gcode_list)
        buttons_layout.addWidget(self.clear_button)

        self.load_button = QPushButton("▶ Load")
        self.load_button.setMinimumHeight(40)
        self.load_button.clicked.connect(self.load_gcode_files)
        buttons_layout.addWidget(self.load_button)

        gcode_layout.addLayout(buttons_layout)
        self.gcode_group.setLayout(gcode_layout)
        middle_column.addWidget(self.gcode_group)
        columns_layout.addLayout(middle_column, 1)

        # Right column - Results
        right_column = QVBoxLayout()
        right_column.setSpacing(16)

        self.results_group = QGroupBox(t("price_summary"))
        self.results_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.results_group.setFixedWidth(320)
        self.results_group.setMinimumHeight(550)
        results_layout = QVBoxLayout()
        results_layout.setSpacing(8)
        results_layout.setContentsMargins(16, 20, 16, 20)
        self.results_group.setLayout(results_layout)

        # Cost row style
        cost_row_style = """
            QWidget {
                background-color: #1a1a2e;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """
        cost_label_style = "color: #a0a0a0; font-size: 12px;"
        cost_value_style = "color: #ffffff; font-size: 13px; font-weight: 600;"
        
        # Result labels
        self.material_cost_label = QLabel("-")
        self.time_cost_label = QLabel("-")
        self.energy_cost_label = QLabel("-")
        self.postprocess_cost_label = QLabel("-")
        self.setup_fee_label = QLabel("-")
        self.risk_label = QLabel("-")
        self.margin_label = QLabel("-")
        self.packaging_label = QLabel("-")
        self.shipping_label = QLabel("-")
        self.vat_label = QLabel("-")
        self.final_price_label = QLabel("-")

        self.result_labels = {}
        
        # === BASE COSTS SECTION ===
        self.base_costs_title = QLabel(t("base_costs_title"))
        self.base_costs_title.setStyleSheet("color: #7c3aed; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 4px 0;")
        results_layout.addWidget(self.base_costs_title)

        # Material cost row
        self.result_labels["material"] = QLabel(t("material_cost"))
        row1 = self._create_cost_row(self.result_labels["material"], self.material_cost_label, "#3b82f6")
        results_layout.addWidget(row1)

        # Time cost row
        self.result_labels["time"] = QLabel(t("time_cost"))
        row2 = self._create_cost_row(self.result_labels["time"], self.time_cost_label, "#8b5cf6")
        results_layout.addWidget(row2)

        # Energy cost row
        self.result_labels["energy"] = QLabel(t("energy_cost"))
        row3 = self._create_cost_row(self.result_labels["energy"], self.energy_cost_label, "#06b6d4")
        results_layout.addWidget(row3)

        # Post-process cost row
        self.result_labels["postprocess"] = QLabel(t("postprocess_cost"))
        row4 = self._create_cost_row(self.result_labels["postprocess"], self.postprocess_cost_label, "#14b8a6")
        results_layout.addWidget(row4)

        # Setup fee row
        self.result_labels["setup"] = QLabel(t("setup_fee"))
        row5 = self._create_cost_row(self.result_labels["setup"], self.setup_fee_label, "#f59e0b")
        results_layout.addWidget(row5)

        results_layout.addSpacing(8)

        # === ADDITIONS SECTION ===
        self.additions_title = QLabel(t("additions_title"))
        self.additions_title.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 4px 0;")
        results_layout.addWidget(self.additions_title)

        # Risk row
        self.result_labels["risk"] = QLabel(t("risk_margin"))
        row6 = self._create_cost_row(self.result_labels["risk"], self.risk_label, "#ef4444")
        results_layout.addWidget(row6)

        # Margin row
        self.result_labels["margin"] = QLabel(t("margin"))
        row7 = self._create_cost_row(self.result_labels["margin"], self.margin_label, "#22c55e")
        results_layout.addWidget(row7)

        # Packaging row
        self.result_labels["packaging"] = QLabel(t("packaging_cost"))
        row8 = self._create_cost_row(self.result_labels["packaging"], self.packaging_label, "#a855f7")
        results_layout.addWidget(row8)

        # Shipping row
        self.result_labels["shipping"] = QLabel(t("shipping_cost"))
        row9 = self._create_cost_row(self.result_labels["shipping"], self.shipping_label, "#ec4899")
        results_layout.addWidget(row9)

        results_layout.addSpacing(12)

        # === FINAL SECTION ===
        self.final_section_title = QLabel(t("final_title"))
        self.final_section_title.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 4px 0;")
        results_layout.addWidget(self.final_section_title)

        # VAT row
        self.result_labels["vat"] = QLabel(t("vat"))
        self.vat_label.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: 700;")
        row10 = self._create_cost_row(self.result_labels["vat"], self.vat_label, "#fbbf24")
        results_layout.addWidget(row10)

        results_layout.addSpacing(12)

        # Final price container
        final_price_container = QWidget()
        final_price_container.setMinimumHeight(100)
        final_price_container.setStyleSheet("""
            QWidget#finalPriceBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:0.5 #6366f1, stop:1 #3b82f6);
                border-radius: 12px;
            }
        """)
        final_price_container.setObjectName("finalPriceBox")
        final_price_layout = QVBoxLayout(final_price_container)
        final_price_layout.setContentsMargins(20, 16, 20, 16)
        final_price_layout.setSpacing(6)

        self.final_price_title = QLabel(t("final_price"))
        self.final_price_title.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; background: transparent;")
        self.final_price_title.setAlignment(Qt.AlignCenter)
        final_price_layout.addWidget(self.final_price_title)

        self.final_price_label.setStyleSheet(
            "color: #ffffff; font-size: 28px; font-weight: 800; background: transparent;"
        )
        self.final_price_label.setAlignment(Qt.AlignCenter)
        final_price_layout.addWidget(self.final_price_label)

        results_layout.addWidget(final_price_container)
        results_layout.addStretch()

        right_column.addWidget(self.results_group)
        columns_layout.addLayout(right_column, 0)

        layout.addLayout(columns_layout)

        # Load filaments into combo
        self.load_filaments()

    def load_filaments(self):
        """Load filaments from inventory into combo box."""
        filaments = load_filaments()
        self.filament_combo.clear()
        self.filament_combo.addItem(t("select_filament"), None)

        for filament in filaments:
            filament_type = filament.get('type', '')
            if filament_type:
                display_text = f"{filament['brand']} - {filament_type} ({filament['current_weight']}g)"
            else:
                display_text = f"{filament['brand']} ({filament['current_weight']}g)"

            color_icon = create_color_icon(filament['color'])
            self.filament_combo.addItem(color_icon, display_text, filament['id'])

    def on_filament_changed(self, index: int):
        """Handle filament selection change."""
        if index <= 0:
            self.current_filament_id = None
            self.current_multicolor_filaments = []  # Clear multicolor when selecting single
            self.filament_combo.setEnabled(True)  # Re-enable combo box
            self.available_weight_label.setText(t("available_weight") + " - g")
            return

        filament_id = self.filament_combo.itemData(index)
        if filament_id:
            filament = get_filament_by_id(filament_id)
            if filament:
                self.current_filament_id = filament_id
                self.current_multicolor_filaments = []  # Clear multicolor when selecting single
                self.filament_combo.setEnabled(True)  # Re-enable combo box
                self.available_weight_label.setText(
                    f"{t('available_weight')} {filament['current_weight']} g"
                )

    def select_gcode_files(self):
        """Open file dialog to select G-code files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, t("select_gcode_files"), "",
            "G-code Files (*.gcode *.gco *.nc *.bgcode);;All Files (*)"
        )

        if file_paths:
            for file_path in file_paths:
                if not any(self.gcode_list.item(i).data(Qt.UserRole) == file_path
                         for i in range(self.gcode_list.count())):
                    item = QListWidgetItem(os.path.basename(file_path))
                    item.setData(Qt.UserRole, file_path)
                    self.gcode_list.addItem(item)

    def clear_gcode_list(self):
        """Clear the G-code files list."""
        self.gcode_list.clear()

    def load_gcode_files(self):
        """Load and parse all G-code files from the list."""
        if self.gcode_list.count() == 0:
            QMessageBox.warning(self, t("import_gcode"), t("no_files_to_load"))
            return

        file_paths = []
        for i in range(self.gcode_list.count()):
            file_path = self.gcode_list.item(i).data(Qt.UserRole)
            if file_path and os.path.exists(file_path):
                file_paths.append(file_path)

        if not file_paths:
            QMessageBox.warning(self, t("import_gcode"), t("no_files_found"))
            return

        total_time = 0.0
        total_filament = 0.0
        materials_found = []
        successful_imports = 0
        multicolor_weights = None  # Will store list of weights if multicolor detected

        for file_path in file_paths:
            result = GCodeParser.parse_gcode(file_path)
            file_time = result.get("time_hours", 0.0)
            file_filament = result.get("filament_weight_g", 0.0)
            file_material = result.get("material_type", "")
            
            # Check for multicolor (multiple weights)
            if "filament_weights_g" in result:
                multicolor_weights = result["filament_weights_g"]

            if file_time > 0 or file_filament > 0:
                successful_imports += 1
                total_time += file_time
                total_filament += file_filament
                if file_material:
                    materials_found.append(file_material)

        if total_time > 0:
            self.print_time_input.setText(f"{total_time:.2f}")

        # Handle multicolor
        if multicolor_weights and len(multicolor_weights) > 1:
            # Show dialog to select filaments for each weight
            dialog = MulticolorFilamentDialog(multicolor_weights, self)
            if dialog.exec_() == QDialog.Accepted:
                self.current_multicolor_filaments = dialog.get_selected_filaments()
                self.current_filament_id = None  # Clear single filament selection
                # Set total weight
                total_multicolor_weight = sum(w['weight'] for w in self.current_multicolor_filaments)
                self.filament_weight_input.setText(f"{total_multicolor_weight:.1f}")
                
                # Update combo box to show multicolor info
                self.filament_combo.setCurrentIndex(0)  # Reset to "Select filament"
                self.filament_combo.setEnabled(False)  # Disable combo box for multicolor
                # Update available weight label to show multicolor info
                filaments_info = "<br>".join([
                    f"• {item['filament']['brand']} - {item['weight']:.2f}g"
                    for item in self.current_multicolor_filaments
                ])
                self.available_weight_label.setText(
                    f"<b>{t('multicolor_selected')}:</b><br>{filaments_info}"
                )
                self.available_weight_label.setMinimumHeight(60 + len(self.current_multicolor_filaments) * 20)
                
                if successful_imports > 0:
                    QMessageBox.information(
                        self, t("import_gcode"),
                        t("import_success_multicolor").format(
                            success=successful_imports, total=len(file_paths),
                            time=f"{total_time:.2f}", weight=f"{total_multicolor_weight:.1f}",
                            filaments=len(multicolor_weights)
                        )
                    )
            else:
                # User cancelled, clear multicolor selection
                self.current_multicolor_filaments = []
                self.filament_combo.setEnabled(True)  # Re-enable combo box
                return
        else:
            # Single filament (normal case)
            self.current_multicolor_filaments = []
            self.filament_combo.setEnabled(True)  # Ensure combo box is enabled
            if total_filament > 0:
                self.filament_weight_input.setText(f"{total_filament:.1f}")

            if successful_imports > 0:
                QMessageBox.information(
                    self, t("import_gcode"),
                    t("import_success").format(
                        success=successful_imports, total=len(file_paths),
                        time=f"{total_time:.2f}", weight=f"{total_filament:.1f}"
                    )
                )
        
        if successful_imports == 0:
            QMessageBox.warning(
                self, t("import_gcode"),
                t("import_no_data").format(total=len(file_paths))
            )

    def update_energy_consumption(self):
        """Automatically calculate and display energy consumption."""
        try:
            print_time_text = self.print_time_input.text().strip()
            if print_time_text:
                print_time = float(print_time_text.replace(',', '.'))
                copies = self.copies_input.value()
                if print_time > 0:
                    energy_kwh = PriceCalculator.calculate_energy_consumption(
                        print_time,
                        self.config["energy"]["printer_power_watts"],
                        self.config["energy"]["preheat_time_minutes"],
                        self.config["energy"]["preheat_power_watts"],
                        copies
                    )
                    self.energy_consumption_label.setText(f"{energy_kwh:.3f} kWh")
                else:
                    self.energy_consumption_label.setText("-")
            else:
                self.energy_consumption_label.setText("-")
        except ValueError:
            self.energy_consumption_label.setText("-")

    def validate_inputs(self) -> Tuple[bool, Optional[str]]:
        """Validate all input fields."""
        # Check if multicolor or single filament is selected
        if not self.current_filament_id and not self.current_multicolor_filaments:
            return False, t("select_filament_first")

        try:
            filament_weight = float(self.filament_weight_input.text().replace(',', '.'))
            if filament_weight <= 0:
                return False, t("filament_must_be_positive")

            print_time = float(self.print_time_input.text().replace(',', '.'))
            if print_time <= 0:
                return False, t("time_must_be_positive")

            # Check filament weights
            if self.current_multicolor_filaments:
                # Multicolor: check each filament
                for multicolor_item in self.current_multicolor_filaments:
                    filament = multicolor_item['filament']
                    weight = multicolor_item['weight']
                    if filament['current_weight'] < weight:
                        return False, t("not_enough_filament").format(weight=filament['current_weight'])
            else:
                # Single filament
                filament = get_filament_by_id(self.current_filament_id)
                if filament and filament['current_weight'] < filament_weight:
                    return False, t("not_enough_filament").format(weight=filament['current_weight'])

            return True, None
        except ValueError:
            return False, t("all_fields_numbers")

    def format_price(self, value: float) -> str:
        """Format price value using current currency."""
        return format_currency(value)

    def calculate_price(self):
        """Calculate and display the price breakdown."""
        is_valid, error_message = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, t("validation_error"), error_message)
            return

        try:
            # Handle multicolor or single filament
            if self.current_multicolor_filaments:
                # Multicolor: calculate weighted average material price
                total_weight = 0.0
                weighted_price_sum = 0.0
                material_data = None  # Will be set from first filament for hourly_rate
                
                for multicolor_item in self.current_multicolor_filaments:
                    filament = multicolor_item['filament']
                    weight = multicolor_item['weight']
                    
                    material_type = filament.get('type', 'PLA').upper()
                    brand = filament.get('brand', '').upper()
                    
                    if material_type not in self.config["materials"]:
                        QMessageBox.warning(self, t("error"), t("material_not_found").format(material=material_type))
                        return
                    
                    # Get material_data for this specific material type
                    current_material_data = self.config["materials"][material_type]
                    
                    # Use first material's data for hourly_rate (needed later)
                    if material_data is None:
                        material_data = current_material_data
                    
                    # Get brands for this specific material type
                    brands = current_material_data.get("brands", {})
                    
                    # Try to find brand (case-insensitive)
                    brand_data = None
                    brand_key = None
                    for key in brands.keys():
                        if key.upper() == brand:
                            brand_key = key
                            brand_data = brands[key]
                            break
                    
                    if brand_data is None:
                        # Show available brands for debugging
                        available_brands = ", ".join(brands.keys()) if brands else "brak"
                        QMessageBox.warning(
                            self, t("error"), 
                            t("brand_not_found_details").format(
                                brand=brand, 
                                material=material_type,
                                available=available_brands
                            )
                        )
                        return
                    price_per_kg = brand_data.get("price_per_kg", 0.0)
                    
                    weighted_price_sum += price_per_kg * weight
                    total_weight += weight
                
                material_price_per_kg = weighted_price_sum / total_weight if total_weight > 0 else 0.0
            else:
                # Single filament
                filament = get_filament_by_id(self.current_filament_id)
                if not filament:
                    QMessageBox.warning(self, t("error"), t("filament_not_found"))
                    return

                # Get material price from config
                material_type = filament.get('type', 'PLA').upper()
                brand = filament.get('brand', '').upper()

                if material_type not in self.config["materials"]:
                    QMessageBox.warning(self, t("error"), t("material_not_found").format(material=material_type))
                    return

                material_data = self.config["materials"][material_type]
                brands = material_data.get("brands", {})
                
                # Try to find brand (case-insensitive)
                brand_data = None
                brand_key = None
                for key in brands.keys():
                    if key.upper() == brand:
                        brand_key = key
                        brand_data = brands[key]
                        break
                
                if brand_data is None:
                    # Show available brands for debugging
                    available_brands = ", ".join(brands.keys()) if brands else "brak"
                    QMessageBox.warning(
                        self, t("error"), 
                        t("brand_not_found_details").format(
                            brand=brand, 
                            material=material_type,
                            available=available_brands
                        )
                    )
                    return
                material_price_per_kg = brand_data.get("price_per_kg", 0.0)

            # Parse inputs
            filament_weight = float(self.filament_weight_input.text().replace(',', '.'))
            print_time = float(self.print_time_input.text().replace(',', '.'))
            copies = self.copies_input.value()

            # Parse advanced inputs
            postprocess_time = 0.0
            if self.advanced_group.isChecked():
                postprocess_text = self.postprocess_time_input.text().strip()
                if postprocess_text:
                    postprocess_time = float(postprocess_text.replace(',', '.'))

            # Calculate energy consumption
            energy_consumption = PriceCalculator.calculate_energy_consumption(
                print_time,
                self.config["energy"]["printer_power_watts"],
                self.config["energy"]["preheat_time_minutes"],
                self.config["energy"]["preheat_power_watts"],
                copies
            )

            # Calculate price
            result = PriceCalculator.calculate_price(
                filament_weight_g=filament_weight,
                material_price_per_kg=material_price_per_kg,
                print_time_hours=print_time,
                hourly_rate=material_data["hourly_rate"],
                energy_consumption_kwh=energy_consumption,
                cost_per_kwh=self.config["energy"]["cost_per_kwh"],
                margin_percent=self.config["pricing"]["margin_percent"],
                copies=copies,
                setup_fee=self.config["advanced"]["setup_fee"],
                postprocess_time_hours=postprocess_time,
                postprocess_rate_per_hour=self.config["advanced"]["postprocess_rate_per_hour"],
                risk_percent=self.config["advanced"]["risk_percent"],
                packaging_cost=self.config["advanced"]["packaging_cost"],
                shipping_cost=self.config["advanced"]["shipping_cost"],
                min_price=self.config["pricing"]["min_price"],
                vat_percent=self.config["pricing"]["vat_percent"],
                round_to=self.config["pricing"]["round_to"]
            )

            # Store result for execute_print
            self.current_price_result = result

            # Display results
            self.material_cost_label.setText(self.format_price(result['material_cost']))
            self.time_cost_label.setText(self.format_price(result['time_cost']))
            self.energy_cost_label.setText(self.format_price(result['energy_cost']))
            self.postprocess_cost_label.setText(self.format_price(result['postprocess_cost']))
            self.setup_fee_label.setText(self.format_price(result['setup_fee']))
            self.risk_label.setText(self.format_price(result['risk_amount']))
            self.margin_label.setText(self.format_price(result['margin_amount']))
            self.packaging_label.setText(self.format_price(result['packaging_cost']))
            self.shipping_label.setText(self.format_price(result['shipping_cost']))
            self.vat_label.setText(self.format_price(result['vat_amount']))
            self.final_price_label.setText(self.format_price(result['final_price']))

        except Exception as e:
            QMessageBox.critical(self, t("calculation_error"), t("calculation_error_msg").format(error=str(e)))

    def execute_print(self):
        """Execute print - subtract weight and save to history."""
        is_valid, error_message = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, t("validation_error"), error_message)
            return

        if not self.current_price_result:
            QMessageBox.warning(self, t("error"), t("calculate_first"))
            return

        try:
            filament_weight = float(self.filament_weight_input.text().replace(',', '.'))
            filament = get_filament_by_id(self.current_filament_id)

            # Get suggested print name from G-code files
            suggested_name = t("print_name_default")
            gcode_file = None
            if self.gcode_list.count() > 0:
                first_file = self.gcode_list.item(0).data(Qt.UserRole)
                if first_file:
                    gcode_file = os.path.basename(first_file)
                    suggested_name = os.path.splitext(gcode_file)[0]

            # Ask user for print name with wider dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(t("enter_print_name"))
            dialog.setMinimumWidth(500)
            dialog_layout = QVBoxLayout(dialog)
            dialog_layout.setSpacing(16)
            dialog_layout.setContentsMargins(20, 20, 20, 20)
            
            prompt_label = QLabel(t("enter_print_name_prompt"))
            dialog_layout.addWidget(prompt_label)
            
            name_input = QLineEdit()
            name_input.setText(suggested_name)
            name_input.selectAll()
            dialog_layout.addWidget(name_input)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            dialog_layout.addWidget(button_box)
            
            if dialog.exec_() != QDialog.Accepted:
                return  # User cancelled
            
            print_name = name_input.text().strip()
            if not print_name:
                print_name = suggested_name

            # Handle multicolor or single filament
            if self.current_multicolor_filaments:
                # Multicolor: save multiple print records
                total_price = self.current_price_result['final_price']
                # Distribute price proportionally by weight
                total_weight = sum(w['weight'] for w in self.current_multicolor_filaments)
                
                for multicolor_item in self.current_multicolor_filaments:
                    filament = multicolor_item['filament']
                    weight = multicolor_item['weight']
                    # Calculate proportional price
                    proportional_price = (weight / total_weight) * total_price if total_weight > 0 else 0
                    
                    add_print(
                        filament_id=filament['id'],
                        print_name=print_name.strip(),
                        weight_used=int(weight),
                        price=proportional_price,
                        gcode_file=gcode_file
                    )
                
                # Show success message with all filaments
                filaments_info = ", ".join([
                    f"{item['filament']['brand']} ({item['weight']:.1f}g)"
                    for item in self.current_multicolor_filaments
                ])
                QMessageBox.information(
                    self, t("success"),
                    t("print_recorded_multicolor_msg").format(
                        name=print_name,
                        filaments=filaments_info,
                        weight=f"{total_weight:.1f}",
                        price=self.format_price(total_price)
                    )
                )
            else:
                # Single filament
                filament = get_filament_by_id(self.current_filament_id)
                add_print(
                    filament_id=self.current_filament_id,
                    print_name=print_name.strip(),
                    weight_used=int(filament_weight),
                    price=self.current_price_result['final_price'],
                    gcode_file=gcode_file
                )

                QMessageBox.information(
                    self, t("success"),
                    t("print_recorded_msg").format(
                        brand=filament['brand'],
                        type=filament.get('type', ''),
                        weight=f"{filament_weight:.1f}",
                        price=self.format_price(self.current_price_result['final_price'])
                    )
                )

            # Refresh filament list and clear inputs
            self.load_filaments()
            self.filament_weight_input.clear()
            self.print_time_input.clear()
            self.gcode_list.clear()
            self.current_price_result = None
            self.current_filament_id = None
            self.current_multicolor_filaments = []
            self.filament_combo.setEnabled(True)  # Re-enable combo box
            self.available_weight_label.setText(t("available_weight") + " - g")

            # Clear results
            for label in [self.material_cost_label, self.time_cost_label, self.energy_cost_label,
                         self.postprocess_cost_label, self.setup_fee_label, self.risk_label,
                         self.margin_label, self.packaging_label, self.shipping_label,
                         self.vat_label, self.final_price_label]:
                label.setText("-")

        except Exception as e:
            QMessageBox.critical(self, t("error"), f"{t('error')}: {str(e)}")

    def update_translations(self):
        """Update all UI text after language change."""
        # Groups
        self.input_group.setTitle(t("filament_selection"))
        self.advanced_group.setTitle(t("advanced"))
        self.gcode_group.setTitle(t("gcode_files"))
        self.results_group.setTitle(t("price_summary"))
        
        # Labels
        self.filament_label.setText("Filament:")
        self.weight_label.setText(t("filament_weight"))
        self.time_label.setText(t("total_time"))
        self.copies_label.setText(t("copies"))
        self.energy_label.setText(t("energy_kwh"))
        self.postprocess_label.setText(t("postprocess_time"))
        self.instructions_label.setText(t("drag_drop_hint"))
        self.final_price_title.setText(t("final_price"))
        self.available_weight_label.setText(t("available_weight") + " - g")
        
        # Price summary section titles
        self.base_costs_title.setText(t("base_costs_title"))
        self.additions_title.setText(t("additions_title"))
        self.final_section_title.setText(t("final_title"))
        
        # Placeholders
        self.filament_weight_input.setPlaceholderText(t("placeholder_weight"))
        self.print_time_input.setPlaceholderText(t("placeholder_time"))
        
        # Buttons
        self.calculate_button.setText(t("calculate"))
        self.execute_button.setText(t("execute_print"))
        self.select_files_button.setText(t("add_files"))
        self.clear_button.setText(t("clear_all"))
        self.load_button.setText(t("load_btn"))
        
        # Result labels
        self.result_labels["material"].setText(t("material_cost"))
        self.result_labels["time"].setText(t("time_cost"))
        self.result_labels["energy"].setText(t("energy_cost"))
        self.result_labels["postprocess"].setText(t("postprocess_cost"))
        self.result_labels["setup"].setText(t("setup_fee"))
        self.result_labels["risk"].setText(t("risk_margin"))
        self.result_labels["margin"].setText(t("margin"))
        self.result_labels["packaging"].setText(t("packaging_cost"))
        self.result_labels["shipping"].setText(t("shipping_cost"))
        self.result_labels["vat"].setText(t("vat"))
        
        # Refresh filament combo (to update select_filament text)
        self.load_filaments()

    def update_currency(self):
        """Update displayed prices after currency change."""
        # Recalculate and update display if we have results
        if self.current_price_result:
            self.material_cost_label.setText(self.format_price(self.current_price_result['material_cost']))
            self.time_cost_label.setText(self.format_price(self.current_price_result['time_cost']))
            self.energy_cost_label.setText(self.format_price(self.current_price_result['energy_cost']))
            self.postprocess_cost_label.setText(self.format_price(self.current_price_result['postprocess_cost']))
            self.setup_fee_label.setText(self.format_price(self.current_price_result['setup_fee']))
            self.risk_label.setText(self.format_price(self.current_price_result['risk_amount']))
            self.margin_label.setText(self.format_price(self.current_price_result['margin_amount']))
            self.packaging_label.setText(self.format_price(self.current_price_result['packaging_cost']))
            self.shipping_label.setText(self.format_price(self.current_price_result['shipping_cost']))
            self.vat_label.setText(self.format_price(self.current_price_result['vat_amount']))
            self.final_price_label.setText(self.format_price(self.current_price_result['final_price']))

