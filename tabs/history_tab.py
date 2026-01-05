"""
History tab for viewing all print records with filtering and summaries.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QPushButton, QMessageBox, QComboBox, QLabel, QDateEdit,
    QCheckBox, QCalendarWidget, QDialog
)
from PyQt5.QtCore import Qt, QDate, QLocale, QEvent, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QColor
from datetime import datetime, timedelta

from utils.db_handler import get_all_prints, get_filament_by_id, delete_print, load_filaments
from utils.translations import t, format_currency


def create_color_icon(color_hex: str, size: int = 16) -> QIcon:
    """Create a square color icon from hex color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color_hex))
    return QIcon(pixmap)


class HistoryTab(QWidget):
    """History tab displaying all print records with filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_prints = []
        self.filtered_prints = []
        self.init_ui()

    def init_ui(self):
        """Initialize the history tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Toolbar with edit and delete buttons and filters
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        
        self.edit_button = QPushButton(t("edit_print_btn"))
        self.edit_button.setFixedHeight(36)
        self.edit_button.clicked.connect(self.edit_selected_print)
        toolbar.addWidget(self.edit_button)
        
        self.delete_button = QPushButton(t("delete_print_btn"))
        self.delete_button.setFixedHeight(36)
        self.delete_button.clicked.connect(self.delete_selected_print)
        toolbar.addWidget(self.delete_button)
        
        toolbar.addSpacing(20)
        
        # Filament filter
        self.filament_filter_label = QLabel(t("filter_by_filament"))
        toolbar.addWidget(self.filament_filter_label)
        
        self.filament_filter = QComboBox()
        self.filament_filter.setMinimumWidth(200)
        self.filament_filter.view().setMinimumWidth(300)
        self.filament_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.filament_filter)
        
        toolbar.addSpacing(20)
        
        # Date range filter
        self.date_from_label = QLabel(t("date_from"))
        toolbar.addWidget(self.date_from_label)
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setMinimumWidth(120)
        # Set default to 7 days ago
        seven_days_ago = QDate.currentDate().addDays(-7)
        self.date_from.setDate(seven_days_ago)
        self.date_from.setLocale(self._get_current_locale())
        self.date_from.dateChanged.connect(self.apply_filters)
        # Style calendar when it's created (after showEvent)
        # Style calendar after widget is shown
        QTimer.singleShot(100, lambda: self._style_date_edit(self.date_from))
        toolbar.addWidget(self.date_from)
        
        self.date_to_label = QLabel(t("date_to"))
        toolbar.addWidget(self.date_to_label)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setMinimumWidth(120)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setLocale(self._get_current_locale())
        self.date_to.dateChanged.connect(self.apply_filters)
        # Style calendar after widget is shown
        QTimer.singleShot(100, lambda: self._style_date_edit(self.date_to))
        toolbar.addWidget(self.date_to)
        
        toolbar.addSpacing(20)
        
        # Clear filters button
        self.clear_filters_button = QPushButton(t("clear_filters"))
        self.clear_filters_button.setFixedHeight(36)
        self.clear_filters_button.clicked.connect(self.clear_filters)
        toolbar.addWidget(self.clear_filters_button)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self._update_table_headers()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
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

        layout.addWidget(self.table)

        # Summary row at bottom
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(30)
        
        summary_layout.addStretch()
        
        # Total weight sum
        self.total_weight_label = QLabel(t("total_weight_sum"))
        self.total_weight_label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        summary_layout.addWidget(self.total_weight_label)
        
        self.total_weight_value = QLabel("0 g")
        self.total_weight_value.setStyleSheet("color: #22c55e; font-size: 15px; font-weight: 700;")
        summary_layout.addWidget(self.total_weight_value)
        
        summary_layout.addSpacing(40)
        
        # Total price sum
        self.total_price_label = QLabel(t("total_price_sum"))
        self.total_price_label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        summary_layout.addWidget(self.total_price_label)
        
        self.total_price_value = QLabel("-")
        self.total_price_value.setStyleSheet("color: #7c3aed; font-size: 15px; font-weight: 700;")
        summary_layout.addWidget(self.total_price_value)
        
        summary_layout.addSpacing(20)
        
        layout.addLayout(summary_layout)

        self.refresh_table()

    def _get_current_locale(self) -> QLocale:
        """Get current locale based on language setting."""
        from utils.translations import get_language
        lang = get_language()
        if lang == "EN":
            return QLocale(QLocale.English, QLocale.UnitedStates)
        else:
            return QLocale(QLocale.Polish, QLocale.Poland)
    
    def _get_calendar_style(self) -> str:
        """Get CSS style for calendar widget."""
        return """
            QCalendarWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
            }
            QCalendarWidget QTableView {
                selection-background-color: #7c3aed;
                selection-color: white;
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                gridline-color: #333;
            }
            QCalendarWidget QTableView:item {
                padding: 4px;
                border: none;
            }
            QCalendarWidget QTableView:item:selected {
                background-color: #7c3aed;
                color: white;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #2a2a2a;
                color: #e0e0e0;
                padding: 8px;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid #333;
            }
            QCalendarWidget QToolButton {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: 600;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #3a3a3a;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth {
                qproperty-icon: none;
            }
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                qproperty-icon: none;
            }
            QCalendarWidget QSpinBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-weight: 600;
            }
        """
    
    def _style_date_edit(self, date_edit: QDateEdit):
        """Apply modern styling and locale to date edit calendar."""
        locale = self._get_current_locale()
        date_edit.setLocale(locale)
        
        # Get calendar widget and style it
        # Calendar widget is created lazily, so we need to ensure it exists
        calendar = date_edit.calendarWidget()
        if calendar:
            calendar.setLocale(locale)
            calendar.setStyleSheet(self._get_calendar_style())
        else:
            # If calendar doesn't exist yet, connect to activated signal
            # This will be called when calendar popup is opened
            def on_calendar_activated():
                cal = date_edit.calendarWidget()
                if cal:
                    cal.setLocale(locale)
                    cal.setStyleSheet(self._get_calendar_style())
            
            # Use a timer to check periodically until calendar is created
            def check_and_style():
                cal = date_edit.calendarWidget()
                if cal:
                    cal.setLocale(locale)
                    cal.setStyleSheet(self._get_calendar_style())
                else:
                    QTimer.singleShot(50, check_and_style)
            
            QTimer.singleShot(50, check_and_style)

    def _update_table_headers(self):
        """Update table headers with translated text."""
        headers = [t("date"), t("filament"), t("print_name"), t("weight_used"), t("price")]
        for i, header_text in enumerate(headers):
            header_item = QTableWidgetItem(header_text)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(i, header_item)

    def _populate_filters(self):
        """Populate filter dropdowns with available options."""
        # Block signals during population
        self.filament_filter.blockSignals(True)
        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        
        # Save current filament selection
        current_filament = self.filament_filter.currentData()
        
        # Clear and repopulate filament filter
        self.filament_filter.clear()
        self.filament_filter.addItem(t("all_filaments"), None)
        
        # Get unique filaments from prints
        filament_ids = set()
        for print_record in self.all_prints:
            fid = print_record.get('filament_id')
            if fid:
                filament_ids.add(fid)
        
        for fid in filament_ids:
            filament = get_filament_by_id(fid)
            if filament:
                color_icon = create_color_icon(filament.get('color', '#888888'))
                filament_type = filament.get('type', '')
                if filament_type:
                    display_text = f"{filament['brand']} - {filament_type}"
                else:
                    display_text = filament['brand']
                self.filament_filter.addItem(color_icon, display_text, fid)
        
        # Restore filament selection
        if current_filament:
            for i in range(self.filament_filter.count()):
                if self.filament_filter.itemData(i) == current_filament:
                    self.filament_filter.setCurrentIndex(i)
                    break
        
        # Set date range based on available prints (only if not already set)
        # Default "from" date is already set to 7 days ago in init_ui
        # Only update "to" date to max date if there are prints
        if self.all_prints:
            # Find max date
            max_date = None
            for print_record in self.all_prints:
                timestamp = datetime.fromisoformat(print_record['timestamp'])
                if max_date is None or timestamp > max_date:
                    max_date = timestamp
            
            # Only set "to" date if it's still at default (today) or if max_date is newer
            current_to_date = self.date_to.date().toPyDate()
            if max_date and max_date.date() > current_to_date:
                self.date_to.setDate(QDate(max_date.year, max_date.month, max_date.day))
        
        self.filament_filter.blockSignals(False)
        self.date_from.blockSignals(False)
        self.date_to.blockSignals(False)

    def apply_filters(self):
        """Apply filters and update table."""
        selected_filament = self.filament_filter.currentData()
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        
        self.filtered_prints = []
        
        for print_record in self.all_prints:
            # Filter by filament
            if selected_filament is not None:
                if print_record.get('filament_id') != selected_filament:
                    continue
            
            # Filter by date range
            timestamp = datetime.fromisoformat(print_record['timestamp'])
            print_date = timestamp.date()
            
            if print_date < date_from or print_date > date_to:
                continue
            
            self.filtered_prints.append(print_record)
        
        self._display_prints(self.filtered_prints)

    def clear_filters(self):
        """Clear all filters."""
        self.filament_filter.setCurrentIndex(0)
        # Reset dates: "from" to 7 days ago, "to" to today
        seven_days_ago = QDate.currentDate().addDays(-7)
        self.date_from.setDate(seven_days_ago)
        self.date_to.setDate(QDate.currentDate())

    def refresh_table(self):
        """Refresh the history table with current data."""
        self.all_prints = get_all_prints()
        self._populate_filters()
        self.apply_filters()

    def _display_prints(self, prints):
        """Display given prints in the table."""
        self.table.setRowCount(len(prints))
        
        total_weight = 0
        total_price = 0.0

        for row, print_record in enumerate(prints):
            # Date column (centered)
            timestamp = datetime.fromisoformat(print_record['timestamp'])
            date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            date_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, date_item)

            # Filament column with color icon (centered)
            filament_id = print_record.get('filament_id')
            filament_text = "Unknown"
            filament_color = "#888888"
            if filament_id:
                filament = get_filament_by_id(filament_id)
                if filament:
                    filament_color = filament.get('color', '#888888')
                    filament_type = filament.get('type', '')
                    if filament_type:
                        filament_text = f"{filament['brand']} - {filament_type}"
                    else:
                        filament_text = filament['brand']

            filament_item = QTableWidgetItem(filament_text)
            filament_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            filament_item.setIcon(create_color_icon(filament_color))
            filament_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, filament_item)

            # Print name column (centered)
            print_name = print_record.get('print_name', 'N/A')
            name_item = QTableWidgetItem(print_name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, name_item)

            # Weight used column (centered)
            weight_used = print_record.get('weight_used', 0)
            weight_item = QTableWidgetItem(f"{weight_used}")
            weight_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            weight_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, weight_item)
            total_weight += weight_used

            # Price column (centered)
            price = print_record.get('price')
            if price is not None:
                price_str = format_currency(price)
                total_price += price
            else:
                price_str = "-"
            price_item = QTableWidgetItem(price_str)
            price_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            price_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, price_item)

        self.table.resizeRowsToContents()
        
        # Update summary
        self.total_weight_value.setText(f"{total_weight} g")
        self.total_price_value.setText(format_currency(total_price))

    def edit_selected_print(self):
        """Edit the selected print record."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, t("error"), "Please select a print to edit.")
            return
        
        row = selected_rows[0].row()
        
        if row >= len(self.filtered_prints):
            return
        
        print_record = self.filtered_prints[row]
        print_id = print_record.get("id")
        
        from dialogs.edit_print_dialog import EditPrintDialog
        dialog = EditPrintDialog(print_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

    def delete_selected_print(self):
        """Delete the selected print record and restore weight to filament."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, t("error"), t("select_print_to_delete"))
            return
        
        row = selected_rows[0].row()
        
        if row >= len(self.filtered_prints):
            return
        
        print_record = self.filtered_prints[row]
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
                self.refresh_table()
            else:
                QMessageBox.warning(self, t("error"), t("delete_failed"))

    def update_translations(self):
        """Update all UI text after language change."""
        self._update_table_headers()
        self.edit_button.setText(t("edit_print_btn"))
        self.delete_button.setText(t("delete_print_btn"))
        self.filament_filter_label.setText(t("filter_by_filament"))
        self.date_from_label.setText(t("date_from"))
        self.date_to_label.setText(t("date_to"))
        self.clear_filters_button.setText(t("clear_filters"))
        self.total_weight_label.setText(t("total_weight_sum"))
        self.total_price_label.setText(t("total_price_sum"))
        # Refresh filters to update "All" options
        current_filament = self.filament_filter.currentData()
        self.filament_filter.blockSignals(True)
        self.filament_filter.setItemText(0, t("all_filaments"))
        self.filament_filter.blockSignals(False)
        # Update calendar locale
        self._style_date_edit(self.date_from)
        self._style_date_edit(self.date_to)

    def update_currency(self):
        """Update displayed prices after currency change."""
        self.apply_filters()
