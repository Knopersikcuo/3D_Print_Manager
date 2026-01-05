"""
Unified 3D Print Manager
Combined application for 3D printing price calculation and filament inventory management.
"""

import sys
import os
from typing import Optional, Dict
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QComboBox, QCheckBox,
    QMessageBox, QFormLayout, QFileDialog, QDialog, QDialogButtonBox,
    QScrollArea, QSpinBox, QDoubleSpinBox, QListWidget, QListWidgetItem,
    QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QColorDialog
)
from PyQt5.QtCore import Qt, QMimeData, QTimer
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor, QBrush, QPixmap, QIcon, QPainter

from utils.db_handler import (
    add_brand, add_filament, add_print, delete_filament,
    get_all_brands, get_filament_by_id, get_filament_history,
    get_spool_weight, load_filaments, update_filament, get_all_prints
)
from utils.gcode_parser import GCodeParser
from utils.price_calculator import PriceCalculator, ConfigManager
from utils.translations import (
    t, toggle_language, register_language_callback, get_language,
    cycle_currency, get_currency, register_currency_callback, format_currency as fmt_currency,
    load_preferences
)


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


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Print Manager")
        self.setMinimumWidth(1400)
        self.setMinimumHeight(800)
        
        # Load user preferences (language and currency)
        load_preferences()
        
        # Load configuration
        self.config = ConfigManager.load_config()
        
        # Apply modern dark theme
        self._apply_theme()
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create tabs
        from tabs.calculator_tab import CalculatorTab
        from tabs.inventory_tab import InventoryTab
        from tabs.history_tab import HistoryTab
        
        self.calculator_tab = CalculatorTab(self.config, self)
        self.inventory_tab = InventoryTab(self)
        self.history_tab = HistoryTab(self)
        
        # New structure: header + content
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #3b82f6);")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 16, 0)
        header_layout.setSpacing(8)
        
        # Tab buttons (custom implementation for header)
        self.tab_buttons = []
        tab_names = ["calculator", "inventory", "history"]
        
        for i, name in enumerate(tab_names):
            btn = QPushButton(t(name))
            btn.setMinimumWidth(140)
            btn.setMinimumHeight(44)
            btn.setProperty("tab_index", i)
            btn.setProperty("tab_name", name)
            btn.clicked.connect(lambda checked, idx=i: self.switch_tab(idx))
            btn.setStyleSheet(self._get_tab_button_style(i == 0))
            self.tab_buttons.append(btn)
            header_layout.addWidget(btn)
        
        header_layout.addStretch()
        
        # Currency combo box in header
        self.currency_combo = QComboBox()
        self.currency_combo.setMinimumWidth(100)
        self.currency_combo.setMinimumHeight(36)
        self._populate_currency_combo()
        self.currency_combo.currentTextChanged.connect(self.on_currency_changed)
        self.currency_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                color: white;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                selection-background-color: #7c3aed;
                color: white;
                padding: 4px;
            }
        """)
        header_layout.addWidget(self.currency_combo)
        
        # Language combo box in header
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(80)
        self.lang_combo.setMinimumHeight(36)
        self._populate_language_combo()
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                color: white;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                selection-background-color: #7c3aed;
                color: white;
                padding: 4px;
            }
        """)
        header_layout.addWidget(self.lang_combo)
        
        # Settings button in header
        self.settings_button = QPushButton(t("settings"))
        self.settings_button.setMinimumWidth(130)
        self.settings_button.setMinimumHeight(36)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                color: white;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
            }
        """)
        header_layout.addWidget(self.settings_button)
        
        main_layout.addWidget(header_widget)
        
        # Stacked content for tabs
        self.content_stack = QWidget()
        self.content_stack_layout = QVBoxLayout(self.content_stack)
        self.content_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.content_stack_layout.setSpacing(0)
        
        # Add all tabs to stack (only one visible at a time)
        self.tab_widgets = [self.calculator_tab, self.inventory_tab, self.history_tab]
        for widget in self.tab_widgets:
            self.content_stack_layout.addWidget(widget)
            widget.setVisible(False)
        self.tab_widgets[0].setVisible(True)
        self.current_tab = 0
        
        main_layout.addWidget(self.content_stack)
        
        # Register for language changes
        register_language_callback(self.update_translations)
        
        # Register for currency changes
        register_currency_callback(self.update_currency)

    def _get_tab_button_style(self, is_active: bool) -> str:
        """Get style for tab button based on active state."""
        if is_active:
            return """
                QPushButton {
                    background: #121212;
                    border: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    color: white;
                }
            """
        else:
            return """
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    border: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 0.8);
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                    color: white;
                }
            """

    def switch_tab(self, index: int):
        """Switch to the specified tab."""
        # Hide all tabs
        for i, widget in enumerate(self.tab_widgets):
            widget.setVisible(i == index)
            self.tab_buttons[i].setStyleSheet(self._get_tab_button_style(i == index))
        
        self.current_tab = index
        
        # Refresh data when switching
        if index == 1:
            self.inventory_tab.refresh_table()
        elif index == 2:
            self.history_tab.refresh_table()

    def update_currency(self):
        """Update UI after currency change."""
        from utils.translations import get_currency, t, CURRENCIES
        current_currency = get_currency()
        
        # Update currency combo selection
        for i in range(self.currency_combo.count()):
            if self.currency_combo.itemData(i) == current_currency:
                self.currency_combo.blockSignals(True)
                self.currency_combo.setCurrentIndex(i)
                self.currency_combo.blockSignals(False)
                break
        
        # Update currency combo text
        self._populate_currency_combo()
        
        # Update child tabs
        if hasattr(self.calculator_tab, 'update_currency'):
            self.calculator_tab.update_currency()
        if hasattr(self.history_tab, 'update_currency'):
            self.history_tab.update_currency()

    def update_translations(self):
        """Update all UI text after language change."""
        from utils.translations import get_language
        current_lang = get_language()
        
        # Update tab buttons
        tab_names = ["calculator", "inventory", "history"]
        for i, name in enumerate(tab_names):
            self.tab_buttons[i].setText(t(name))
        
        # Update header buttons
        self.settings_button.setText(t("settings"))
        
        # Update language combo
        self._populate_language_combo()
        
        # Update currency combo (to update translations)
        self._populate_currency_combo()
        
        # Update child tabs
        if hasattr(self.calculator_tab, 'update_translations'):
            self.calculator_tab.update_translations()
        if hasattr(self.inventory_tab, 'update_translations'):
            self.inventory_tab.update_translations()
        if hasattr(self.history_tab, 'update_translations'):
            self.history_tab.update_translations()

    def _apply_theme(self):
        """Apply modern dark theme with purple/blue accents."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #333;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 16px;
                font-weight: 600;
                font-size: 11px;
                color: #b0b0b0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                color: #ffffff;
                selection-background-color: #7c3aed;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #7c3aed;
                background-color: #252525;
            }
            QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid #555;
                background-color: #222;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                selection-background-color: #7c3aed;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7c3aed, stop:1 #6d28d9);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8b5cf6, stop:1 #7c3aed);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6d28d9, stop:1 #5b21b6);
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
                gridline-color: #333;
                selection-background-color: #7c3aed;
            }
            QTableWidget::item {
                padding: 8px;
                color: #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #7c3aed;
                color: white;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #e0e0e0;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #7c3aed;
                font-weight: 600;
            }
        """)

    def on_tab_changed(self, index: int):
        """Handle tab change to refresh data."""
        if index == 1:  # Inventory tab
            self.inventory_tab.refresh_table()
        elif index == 2:  # History tab
            self.history_tab.refresh_table()

    def _populate_currency_combo(self):
        """Populate currency combo box with available currencies."""
        from utils.translations import CURRENCIES, get_currency, t
        self.currency_combo.blockSignals(True)
        self.currency_combo.clear()
        
        current_currency = get_currency()
        for currency_code in CURRENCIES.keys():
            if currency_code == "PLN":
                display_text = t("currency_pln")
            elif currency_code == "EUR":
                display_text = t("currency_eur")
            elif currency_code == "USD":
                display_text = t("currency_usd")
            elif currency_code == "GBP":
                display_text = t("currency_gbp")
            else:
                display_text = f"💰 {currency_code}"
            
            self.currency_combo.addItem(display_text, currency_code)
            if currency_code == current_currency:
                self.currency_combo.setCurrentIndex(self.currency_combo.count() - 1)
        
        self.currency_combo.blockSignals(False)
    
    def _populate_language_combo(self):
        """Populate language combo box with available languages."""
        from utils.translations import get_language, t
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        
        current_lang = get_language()
        # Add Polish
        self.lang_combo.addItem(t("language_pl"), "PL")
        if current_lang == "PL":
            self.lang_combo.setCurrentIndex(0)
        
        # Add English
        self.lang_combo.addItem(t("language_en"), "EN")
        if current_lang == "EN":
            self.lang_combo.setCurrentIndex(1)
        
        self.lang_combo.blockSignals(False)
    
    def on_currency_changed(self, text):
        """Handle currency selection change."""
        from utils.translations import set_currency
        currency_code = self.currency_combo.currentData()
        if currency_code:
            set_currency(currency_code)
    
    def on_language_changed(self, text):
        """Handle language selection change."""
        from utils.translations import set_language
        lang_code = self.lang_combo.currentData()
        if lang_code:
            set_language(lang_code)

    def open_settings(self):
        """Open settings dialog."""
        from dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.get_config()
            ConfigManager.save_config(self.config)
            self.calculator_tab.config = self.config
            QMessageBox.information(self, t("settings_title"), t("settings_saved"))


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
