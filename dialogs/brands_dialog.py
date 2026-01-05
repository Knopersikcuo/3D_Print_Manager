"""
Dialog for managing brands.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt

from utils.db_handler import add_brand, load_brands, update_brand, delete_brand, get_brand_by_id
from utils.translations import t, register_language_callback


class BrandsDialog(QDialog):
    """Dialog for managing brands."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editing_brand_id = None  # Track which brand is being edited
        self.main_window = None  # Will be set for refreshing calculator
        self.init_ui()
        # Register for language updates
        register_language_callback(self.update_translations)
    
    def set_main_window(self, main_window):
        """Set reference to main window for refreshing calculator tab."""
        self.main_window = main_window

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle(t("brands_title"))
        self.setModal(True)
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(layout)

        self.title_label = QLabel(t("brands_title_full"))
        self.title_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Action buttons toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        self.edit_btn = QPushButton(t("edit_btn"))
        self.edit_btn.setFixedHeight(36)
        self.edit_btn.clicked.connect(self.edit_brand)
        toolbar_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton(t("delete_btn"))
        self.delete_btn.setFixedHeight(36)
        self.delete_btn.clicked.connect(self.delete_brand)
        toolbar_layout.addWidget(self.delete_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # Brands table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self._update_table_headers()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
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

        # Add brand section
        self.add_section_label = QLabel(t("add_new_brand"))
        self.add_section_label.setStyleSheet("font-size: 10pt; font-weight: bold; margin-top: 10px;")
        layout.addWidget(self.add_section_label)

        add_form_layout = QHBoxLayout()
        add_form_layout.setSpacing(10)

        self.name_title_label = QLabel(t("name_label"))
        add_form_layout.addWidget(self.name_title_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("placeholder_brand"))
        add_form_layout.addWidget(self.name_input)

        self.spool_weight_title_label = QLabel(t("spool_weight"))
        add_form_layout.addWidget(self.spool_weight_title_label)
        self.weight_input = QSpinBox()
        self.weight_input.setRange(1, 1000)
        self.weight_input.setValue(150)
        add_form_layout.addWidget(self.weight_input)

        self.add_btn = QPushButton(t("add_btn"))
        self.add_btn.clicked.connect(self.add_brand)
        add_form_layout.addWidget(self.add_btn)

        add_form_layout.addStretch()

        self.close_btn = QPushButton(t("close"))
        self.close_btn.clicked.connect(self.reject)
        add_form_layout.addWidget(self.close_btn)

        layout.addLayout(add_form_layout)

        self.refresh_table()

    def _update_table_headers(self):
        """Update table headers with translated text."""
        headers = [t("brand"), t("spool_weight")]
        for i, header_text in enumerate(headers):
            header_item = QTableWidgetItem(header_text)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(i, header_item)

    def refresh_table(self):
        """Refresh the brands table."""
        brands = load_brands()
        self.table.setRowCount(len(brands))

        for row, brand in enumerate(brands):
            name_item = QTableWidgetItem(brand['name'])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            # Store brand ID in item data
            name_item.setData(Qt.UserRole, brand.get('id'))
            self.table.setItem(row, 0, name_item)

            weight_item = QTableWidgetItem(f"{brand['spool_weight']} g")
            weight_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            weight_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(row, 1, weight_item)

        self.table.resizeRowsToContents()
    
    def get_selected_brand_id(self):
        """Get ID of selected brand."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        name_item = self.table.item(row, 0)
        if name_item:
            return name_item.data(Qt.UserRole)
        return None

    def add_brand(self):
        """Add a new brand or update existing one."""
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, t("error"), t("brand_name_required"))
            return

        try:
            if self.editing_brand_id:
                # Update existing brand
                update_brand(
                    brand_id=self.editing_brand_id,
                    name=name,
                    spool_weight=self.weight_input.value()
                )
                QMessageBox.information(self, t("success"), t("brand_updated").format(name=name))
                self.editing_brand_id = None
                self.add_btn.setText(t("add_btn"))
                self.add_section_label.setText(t("add_new_brand"))
            else:
                # Add new brand
                add_brand(name=name, spool_weight=self.weight_input.value())
                QMessageBox.information(self, t("success"), t("brand_added").format(name=name))
                # Refresh calculator tab filament list (brands may be needed for filament creation)
                if self.main_window:
                    self.main_window.refresh_calculator_filaments()
            
            self.name_input.clear()
            self.weight_input.setValue(150)
            self.refresh_table()
        except ValueError as e:
            QMessageBox.warning(self, t("error"), str(e))
        except Exception as e:
            if self.editing_brand_id:
                QMessageBox.critical(self, t("error"), t("update_brand_error").format(error=str(e)))
            else:
                QMessageBox.critical(self, t("error"), t("add_brand_error").format(error=str(e)))
    
    def edit_brand(self):
        """Edit selected brand."""
        brand_id = self.get_selected_brand_id()
        if not brand_id:
            QMessageBox.warning(self, t("error"), t("select_brand_to_edit"))
            return
        
        brand = get_brand_by_id(brand_id)
        if not brand:
            QMessageBox.warning(self, t("error"), "Brand not found.")
            return
        
        # Load brand data into form
        self.editing_brand_id = brand_id
        self.name_input.setText(brand['name'])
        self.weight_input.setValue(brand.get('spool_weight', 150))
        self.add_btn.setText(t("save_changes"))
        self.add_section_label.setText(t("edit_brand_title"))
        
        # Scroll to input fields
        self.name_input.setFocus()
    
    def delete_brand(self):
        """Delete selected brand."""
        brand_id = self.get_selected_brand_id()
        if not brand_id:
            QMessageBox.warning(self, t("error"), t("select_brand_to_delete"))
            return
        
        brand = get_brand_by_id(brand_id)
        if not brand:
            QMessageBox.warning(self, t("error"), "Brand not found.")
            return
        
        brand_name = brand['name']
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            t("confirm_delete"),
            t("confirm_delete_brand").format(name=brand_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if delete_brand(brand_id):
                    QMessageBox.information(self, t("success"), t("brand_deleted").format(name=brand_name))
                    # Clear edit mode if deleting edited brand
                    if self.editing_brand_id == brand_id:
                        self.editing_brand_id = None
                        self.name_input.clear()
                        self.weight_input.setValue(150)
                        self.add_btn.setText(t("add_btn"))
                        self.add_section_label.setText(t("add_new_brand"))
                    self.refresh_table()
                else:
                    QMessageBox.warning(self, t("error"), "Failed to delete brand.")
            except ValueError as e:
                QMessageBox.warning(self, t("error"), str(e))
            except Exception as e:
                QMessageBox.critical(self, t("error"), t("delete_brand_error").format(error=str(e)))
    
    def update_translations(self):
        """Update all UI text after language change."""
        self.setWindowTitle(t("brands_title"))
        self.title_label.setText(t("brands_title_full"))
        self._update_table_headers()
        self.add_section_label.setText(t("add_new_brand") if not self.editing_brand_id else t("edit_brand_title"))
        self.name_title_label.setText(t("name_label"))
        self.spool_weight_title_label.setText(t("spool_weight"))
        self.edit_btn.setText(t("edit_btn"))
        self.delete_btn.setText(t("delete_btn"))
        self.add_btn.setText(t("add_btn") if not self.editing_brand_id else t("save_changes"))
        self.close_btn.setText(t("close"))
