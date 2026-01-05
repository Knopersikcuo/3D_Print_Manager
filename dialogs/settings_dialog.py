"""
Settings dialog for configuring calculator parameters.
"""

from typing import Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox,
    QDialogButtonBox, QScrollArea, QWidget, QLabel, QPushButton
)
from PyQt5.QtCore import Qt

from utils.price_calculator import ConfigManager
from utils.db_handler import load_brands
from utils.translations import (
    t, register_language_callback, register_currency_callback,
    get_currency_symbol, get_currency_per_hour, get_currency_per_kg, get_currency_per_kwh,
    convert_from_pln, convert_to_pln, get_currency
)


class CollapsibleGroupBox(QWidget):
    """A collapsible group box widget with toggle button."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.base_title = title  # Store original title without arrow
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 0, 15, 15)
        self.content_layout.setSpacing(10)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toggle button
        self.toggle_button = QPushButton()
        self.toggle_button.setCheckable(False)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 12pt;
                padding: 10px 15px;
                border: 2px solid #7c3aed;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle)
        main_layout.addWidget(self.toggle_button)
        
        # Content widget (initially hidden)
        main_layout.addWidget(self.content_widget)
        self.content_widget.setVisible(False)
        
        self._update_button_text()
    
    def toggle(self):
        """Toggle the expanded/collapsed state."""
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self._update_button_text()
    
    def _update_button_text(self):
        """Update button text with arrow indicator."""
        arrow = "▼" if self.is_expanded else "▶"
        self.toggle_button.setText(f"{arrow} {self.base_title}")
    
    def setTitle(self, title: str):
        """Set the title of the collapsible group."""
        self.base_title = title
        self._update_button_text()
    
    def layout(self):
        """Return the content layout for adding widgets."""
        return self.content_layout
    
    def setStyleSheet(self, style: str):
        """Set custom stylesheet for the toggle button."""
        self.toggle_button.setStyleSheet(style)


class SettingsDialog(QDialog):
    """Settings dialog for configuring calculator parameters."""

    def __init__(self, config: Dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        # Store current currency to track changes
        self.current_currency = get_currency()
        # Synchronize brands from inventory with config
        self._sync_brands_from_inventory()
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        
        # Register for language and currency updates
        register_language_callback(self.update_translations)
        register_currency_callback(self.update_currency)
    
    def _sync_brands_from_inventory(self):
        """Sync brands from inventory (brands.json) to config for all materials."""
        inventory_brands = load_brands()
        inventory_brand_names = {brand['name'].upper() for brand in inventory_brands}
        
        # For each material, sync brands with inventory
        for material_name, material_data in self.config["materials"].items():
            if "brands" not in material_data:
                material_data["brands"] = {}
            
            existing_brands = {brand.upper() for brand in material_data["brands"].keys()}
            
            # Remove brands that are no longer in inventory
            brands_to_remove = []
            for brand_name in material_data["brands"].keys():
                if brand_name.upper() not in inventory_brand_names:
                    brands_to_remove.append(brand_name)
            
            for brand_name in brands_to_remove:
                del material_data["brands"][brand_name]
            
            # Add missing brands from inventory with default price (0.0)
            for brand_name_upper in inventory_brand_names:
                if brand_name_upper not in existing_brands:
                    # Find original case from inventory
                    original_brand_name = next(
                        (b['name'] for b in inventory_brands if b['name'].upper() == brand_name_upper),
                        brand_name_upper
                    )
                    material_data["brands"][original_brand_name] = {
                        "price_per_kg": 0.0
                    }

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        # Materials section - each material as collapsible group
        materials_label = QLabel(f"<b>{t('materials_section')}</b>")
        materials_label.setStyleSheet("font-size: 14pt; padding: 10px 0px;")
        scroll_layout.addWidget(materials_label)
        
        self.material_inputs = {}
        self.material_groups = {}  # Store material group boxes for translation updates

        for material_name, material_data in self.config["materials"].items():
            # Create collapsible group box for each material
            material_group = CollapsibleGroupBox(material_name)
            material_group.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    font-weight: bold;
                    font-size: 12pt;
                    padding: 10px 15px;
                    border: 2px solid #7c3aed;
                    border-radius: 8px;
                    background-color: #2a2a2a;
                    color: #ffffff;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
                QPushButton:pressed {
                    background-color: #1a1a1a;
                }
            """)
            
            material_layout = material_group.layout()

            # Hourly rate (convert from PLN to current currency)
            rate_input = QDoubleSpinBox()
            rate_input.setRange(0, 1000)
            rate_pln = material_data.get("hourly_rate", 5.0)
            rate_input.setValue(convert_from_pln(rate_pln))
            rate_input.setSuffix(f" {get_currency_per_hour()}")
            rate_input.setDecimals(2)

            rate_layout = QFormLayout()
            rate_label = QLabel(t("hourly_rate_label"))
            rate_layout.addRow(rate_label, rate_input)
            material_layout.addLayout(rate_layout)

            # Brands section
            brands = material_data.get("brands", {})
            brands_label = QLabel(f"<b>{t('brands_label')}</b>")
            brands_label.setStyleSheet("font-size: 11pt; padding-top: 10px;")
            material_layout.addWidget(brands_label)

            brand_inputs = {}
            for brand_name, brand_data in brands.items():
                brand_price_input = QDoubleSpinBox()
                brand_price_input.setRange(0, 10000)
                price_pln = brand_data.get("price_per_kg", 0.0)
                brand_price_input.setValue(convert_from_pln(price_pln))
                brand_price_input.setSuffix(f" {get_currency_per_kg()}")
                brand_price_input.setDecimals(2)

                brand_layout = QFormLayout()
                brand_layout.setContentsMargins(20, 0, 0, 0)
                brand_name_label = QLabel(f"{brand_name}:")
                brand_layout.addRow(brand_name_label, brand_price_input)
                material_layout.addLayout(brand_layout)

                brand_inputs[brand_name] = {
                    "input": brand_price_input,
                    "label": brand_name_label
                }

            scroll_layout.addWidget(material_group)
            
            self.material_inputs[material_name] = {
                "rate": rate_input,
                "rate_label": rate_label,
                "brands": brand_inputs,
                "brands_label": brands_label,
                "group": material_group
            }
            self.material_groups[material_name] = material_group

        # Energy section
        energy_group = CollapsibleGroupBox(t("energy_section"))
        energy_group.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 12pt;
                padding: 10px 15px;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        energy_layout = QFormLayout()
        energy_layout.setContentsMargins(0, 10, 0, 0)
        energy_layout.setSpacing(10)

        self.cost_per_kwh_input = QDoubleSpinBox()
        self.cost_per_kwh_input.setRange(0, 10)
        cost_pln = self.config["energy"]["cost_per_kwh"]
        self.cost_per_kwh_input.setValue(convert_from_pln(cost_pln))
        self.cost_per_kwh_input.setSuffix(f" {get_currency_per_kwh()}")
        self.cost_per_kwh_input.setDecimals(2)

        self.power_watts_input = QDoubleSpinBox()
        self.power_watts_input.setRange(0, 10000)
        self.power_watts_input.setValue(self.config["energy"]["printer_power_watts"])
        self.power_watts_input.setSuffix(" W")
        self.power_watts_input.setDecimals(1)

        self.preheat_time_input = QDoubleSpinBox()
        self.preheat_time_input.setRange(0, 60)
        self.preheat_time_input.setValue(self.config["energy"]["preheat_time_minutes"])
        self.preheat_time_input.setSuffix(" min")
        self.preheat_time_input.setDecimals(1)

        self.preheat_power_input = QDoubleSpinBox()
        self.preheat_power_input.setRange(0, 10000)
        self.preheat_power_input.setValue(self.config["energy"]["preheat_power_watts"])
        self.preheat_power_input.setSuffix(" W")
        self.preheat_power_input.setDecimals(1)

        self.cost_per_kwh_label = QLabel(t("cost_per_kwh_label"))
        self.power_watts_label = QLabel(t("printer_power_label"))
        self.preheat_time_label = QLabel(t("preheat_time_label"))
        self.preheat_power_label = QLabel(t("preheat_power_label"))

        energy_layout.addRow(self.cost_per_kwh_label, self.cost_per_kwh_input)
        energy_layout.addRow(self.power_watts_label, self.power_watts_input)
        energy_layout.addRow(self.preheat_time_label, self.preheat_time_input)
        energy_layout.addRow(self.preheat_power_label, self.preheat_power_input)
        energy_group.layout().addLayout(energy_layout)
        scroll_layout.addWidget(energy_group)
        self.energy_group = energy_group

        # Pricing section
        pricing_group = CollapsibleGroupBox(t("pricing_section"))
        pricing_group.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 12pt;
                padding: 10px 15px;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        pricing_layout = QFormLayout()
        pricing_layout.setContentsMargins(0, 10, 0, 0)
        pricing_layout.setSpacing(10)

        self.margin_input = QDoubleSpinBox()
        self.margin_input.setRange(0, 100)
        self.margin_input.setValue(self.config["pricing"]["margin_percent"])
        self.margin_input.setSuffix(" %")
        self.margin_input.setDecimals(1)

        self.vat_input = QDoubleSpinBox()
        self.vat_input.setRange(0, 100)
        self.vat_input.setValue(self.config["pricing"]["vat_percent"])
        self.vat_input.setSuffix(" %")
        self.vat_input.setDecimals(1)

        self.min_price_input = QDoubleSpinBox()
        self.min_price_input.setRange(0, 10000)
        min_price_pln = self.config["pricing"]["min_price"]
        self.min_price_input.setValue(convert_from_pln(min_price_pln))
        self.min_price_input.setSuffix(f" {get_currency_symbol()}")
        self.min_price_input.setDecimals(2)

        self.round_to_input = QDoubleSpinBox()
        self.round_to_input.setRange(0, 1)
        round_to_pln = self.config["pricing"]["round_to"]
        self.round_to_input.setValue(convert_from_pln(round_to_pln))
        self.round_to_input.setSuffix(f" {get_currency_symbol()}")
        self.round_to_input.setDecimals(2)
        self.round_to_input.setSingleStep(0.05)

        self.margin_label = QLabel(t("margin_label"))
        self.vat_label = QLabel(t("vat_label"))
        self.min_price_label = QLabel(t("min_price_label"))
        self.round_to_label = QLabel(t("round_to_label"))

        pricing_layout.addRow(self.margin_label, self.margin_input)
        pricing_layout.addRow(self.vat_label, self.vat_input)
        pricing_layout.addRow(self.min_price_label, self.min_price_input)
        pricing_layout.addRow(self.round_to_label, self.round_to_input)
        pricing_group.layout().addLayout(pricing_layout)
        scroll_layout.addWidget(pricing_group)
        self.pricing_group = pricing_group

        # Advanced section
        advanced_group = CollapsibleGroupBox(t("advanced_section"))
        advanced_group.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 12pt;
                padding: 10px 15px;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        advanced_layout = QFormLayout()
        advanced_layout.setContentsMargins(0, 10, 0, 0)
        advanced_layout.setSpacing(10)

        self.setup_fee_input = QDoubleSpinBox()
        self.setup_fee_input.setRange(0, 10000)
        setup_fee_pln = self.config["advanced"]["setup_fee"]
        self.setup_fee_input.setValue(convert_from_pln(setup_fee_pln))
        self.setup_fee_input.setSuffix(f" {get_currency_symbol()}")
        self.setup_fee_input.setDecimals(2)

        self.postprocess_rate_input = QDoubleSpinBox()
        self.postprocess_rate_input.setRange(0, 1000)
        postprocess_rate_pln = self.config["advanced"]["postprocess_rate_per_hour"]
        self.postprocess_rate_input.setValue(convert_from_pln(postprocess_rate_pln))
        self.postprocess_rate_input.setSuffix(f" {get_currency_per_hour()}")
        self.postprocess_rate_input.setDecimals(2)

        self.risk_input = QDoubleSpinBox()
        self.risk_input.setRange(0, 100)
        self.risk_input.setValue(self.config["advanced"]["risk_percent"])
        self.risk_input.setSuffix(" %")
        self.risk_input.setDecimals(1)

        self.packaging_input = QDoubleSpinBox()
        self.packaging_input.setRange(0, 1000)
        packaging_pln = self.config["advanced"]["packaging_cost"]
        self.packaging_input.setValue(convert_from_pln(packaging_pln))
        self.packaging_input.setSuffix(f" {get_currency_symbol()}")
        self.packaging_input.setDecimals(2)

        self.shipping_input = QDoubleSpinBox()
        self.shipping_input.setRange(0, 1000)
        shipping_pln = self.config["advanced"]["shipping_cost"]
        self.shipping_input.setValue(convert_from_pln(shipping_pln))
        self.shipping_input.setSuffix(f" {get_currency_symbol()}")
        self.shipping_input.setDecimals(2)

        self.setup_fee_label = QLabel(t("setup_fee_label"))
        self.postprocess_rate_label = QLabel(t("postprocess_rate_label"))
        self.risk_label = QLabel(t("risk_label"))
        self.packaging_label = QLabel(t("packaging_label"))
        self.shipping_label = QLabel(t("shipping_label"))

        advanced_layout.addRow(self.setup_fee_label, self.setup_fee_input)
        advanced_layout.addRow(self.postprocess_rate_label, self.postprocess_rate_input)
        advanced_layout.addRow(self.risk_label, self.risk_input)
        advanced_layout.addRow(self.packaging_label, self.packaging_input)
        advanced_layout.addRow(self.shipping_label, self.shipping_input)
        advanced_group.layout().addLayout(advanced_layout)
        scroll_layout.addWidget(advanced_group)
        self.advanced_group = advanced_group

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.cancel_button = buttons.button(QDialogButtonBox.Cancel)
        self.ok_button.setText(t("ok"))
        self.cancel_button.setText(t("cancel"))
        layout.addWidget(buttons)

    def get_config(self) -> Dict:
        """Get updated configuration from dialog inputs, converting values from current currency to PLN."""
        config = self.config.copy()

        # Update materials (convert from current currency to PLN)
        for material_name, inputs in self.material_inputs.items():
            rate_current = inputs["rate"].value()
            config["materials"][material_name]["hourly_rate"] = convert_to_pln(rate_current)
            if "brands" in inputs:
                for brand_name, brand_data in inputs["brands"].items():
                    if "brands" not in config["materials"][material_name]:
                        config["materials"][material_name]["brands"] = {}
                    if brand_name not in config["materials"][material_name]["brands"]:
                        config["materials"][material_name]["brands"][brand_name] = {}
                    price_current = brand_data["input"].value()
                    config["materials"][material_name]["brands"][brand_name]["price_per_kg"] = convert_to_pln(price_current)

        # Update energy (convert cost_per_kwh from current currency to PLN)
        cost_current = self.cost_per_kwh_input.value()
        config["energy"]["cost_per_kwh"] = convert_to_pln(cost_current)
        config["energy"]["printer_power_watts"] = self.power_watts_input.value()
        config["energy"]["preheat_time_minutes"] = self.preheat_time_input.value()
        config["energy"]["preheat_power_watts"] = self.preheat_power_input.value()

        # Update pricing (convert min_price and round_to from current currency to PLN)
        config["pricing"]["margin_percent"] = self.margin_input.value()
        config["pricing"]["vat_percent"] = self.vat_input.value()
        min_price_current = self.min_price_input.value()
        config["pricing"]["min_price"] = convert_to_pln(min_price_current)
        round_to_current = self.round_to_input.value()
        config["pricing"]["round_to"] = convert_to_pln(round_to_current)

        # Update advanced (convert monetary values from current currency to PLN)
        setup_fee_current = self.setup_fee_input.value()
        config["advanced"]["setup_fee"] = convert_to_pln(setup_fee_current)
        postprocess_rate_current = self.postprocess_rate_input.value()
        config["advanced"]["postprocess_rate_per_hour"] = convert_to_pln(postprocess_rate_current)
        config["advanced"]["risk_percent"] = self.risk_input.value()
        packaging_current = self.packaging_input.value()
        config["advanced"]["packaging_cost"] = convert_to_pln(packaging_current)
        shipping_current = self.shipping_input.value()
        config["advanced"]["shipping_cost"] = convert_to_pln(shipping_current)

        return config

    def update_translations(self):
        """Update all translatable texts in the dialog."""
        self.setWindowTitle(t("settings_title"))
        
        # Update section labels
        if hasattr(self, 'energy_group'):
            self.energy_group.setTitle(t("energy_section"))
        if hasattr(self, 'pricing_group'):
            self.pricing_group.setTitle(t("pricing_section"))
        if hasattr(self, 'advanced_group'):
            self.advanced_group.setTitle(t("advanced_section"))
        
        # Update material group titles
        for material_name, inputs in self.material_inputs.items():
            if "group" in inputs:
                inputs["group"].setTitle(material_name)
        
        # Update button texts
        if hasattr(self, 'ok_button'):
            self.ok_button.setText(t("ok"))
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setText(t("cancel"))
        
        # Update material groups and labels
        for material_name, inputs in self.material_inputs.items():
            if "rate_label" in inputs:
                inputs["rate_label"].setText(t("hourly_rate_label"))
            if "brands_label" in inputs:
                inputs["brands_label"].setText(f"<b>{t('brands_label')}</b>")
            # Update suffixes
            inputs["rate"].setSuffix(f" {get_currency_per_hour()}")
            for brand_name, brand_data in inputs["brands"].items():
                brand_data["input"].setSuffix(f" {get_currency_per_kg()}")
        
        # Update energy labels
        if hasattr(self, 'cost_per_kwh_label'):
            self.cost_per_kwh_label.setText(t("cost_per_kwh_label"))
            self.power_watts_label.setText(t("printer_power_label"))
            self.preheat_time_label.setText(t("preheat_time_label"))
            self.preheat_power_label.setText(t("preheat_power_label"))
            self.cost_per_kwh_input.setSuffix(f" {get_currency_per_kwh()}")
        
        # Update pricing labels
        if hasattr(self, 'margin_label'):
            self.margin_label.setText(t("margin_label"))
            self.vat_label.setText(t("vat_label"))
            self.min_price_label.setText(t("min_price_label"))
            self.round_to_label.setText(t("round_to_label"))
            self.min_price_input.setSuffix(f" {get_currency_symbol()}")
            self.round_to_input.setSuffix(f" {get_currency_symbol()}")
        
        # Update advanced labels
        if hasattr(self, 'setup_fee_label'):
            self.setup_fee_label.setText(t("setup_fee_label"))
            self.postprocess_rate_label.setText(t("postprocess_rate_label"))
            self.risk_label.setText(t("risk_label"))
            self.packaging_label.setText(t("packaging_label"))
            self.shipping_label.setText(t("shipping_label"))
            self.setup_fee_input.setSuffix(f" {get_currency_symbol()}")
            self.postprocess_rate_input.setSuffix(f" {get_currency_per_hour()}")
            self.packaging_input.setSuffix(f" {get_currency_symbol()}")
            self.shipping_input.setSuffix(f" {get_currency_symbol()}")

    def update_currency(self):
        """Update currency suffixes and convert values after currency change."""
        # Get new currency
        new_currency = get_currency()
        
        # If currency changed, convert all values
        if new_currency != self.current_currency:
            # Convert all values: current currency -> PLN -> new currency
            # Materials
            for material_name, inputs in self.material_inputs.items():
                rate_current = inputs["rate"].value()
                rate_pln = convert_to_pln(rate_current)
                inputs["rate"].setValue(convert_from_pln(rate_pln))
                
                for brand_name, brand_data in inputs["brands"].items():
                    price_current = brand_data["input"].value()
                    price_pln = convert_to_pln(price_current)
                    brand_data["input"].setValue(convert_from_pln(price_pln))
            
            # Energy
            cost_current = self.cost_per_kwh_input.value()
            cost_pln = convert_to_pln(cost_current)
            self.cost_per_kwh_input.setValue(convert_from_pln(cost_pln))
            
            # Pricing
            min_price_current = self.min_price_input.value()
            min_price_pln = convert_to_pln(min_price_current)
            self.min_price_input.setValue(convert_from_pln(min_price_pln))
            
            round_to_current = self.round_to_input.value()
            round_to_pln = convert_to_pln(round_to_current)
            self.round_to_input.setValue(convert_from_pln(round_to_pln))
            
            # Advanced
            setup_fee_current = self.setup_fee_input.value()
            setup_fee_pln = convert_to_pln(setup_fee_current)
            self.setup_fee_input.setValue(convert_from_pln(setup_fee_pln))
            
            postprocess_rate_current = self.postprocess_rate_input.value()
            postprocess_rate_pln = convert_to_pln(postprocess_rate_current)
            self.postprocess_rate_input.setValue(convert_from_pln(postprocess_rate_pln))
            
            packaging_current = self.packaging_input.value()
            packaging_pln = convert_to_pln(packaging_current)
            self.packaging_input.setValue(convert_from_pln(packaging_pln))
            
            shipping_current = self.shipping_input.value()
            shipping_pln = convert_to_pln(shipping_current)
            self.shipping_input.setValue(convert_from_pln(shipping_pln))
            
            # Update current currency
            self.current_currency = new_currency
        
        # Update suffixes
        self.update_translations()

