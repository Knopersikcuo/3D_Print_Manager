"""
Price calculator and configuration manager for 3D printing service pricing.
"""

import json
import os
from typing import Dict

# Configuration file path - always in the same directory as the script file
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "data", "calculator_config.json")

# Default configuration values
DEFAULT_CONFIG = {
    "materials": {
        "PLA": {
            "hourly_rate": 5.0,
            "brands": {}
        },
        "PETG": {
            "hourly_rate": 5.5,
            "brands": {}
        },
        "ABS": {
            "hourly_rate": 6.0,
            "brands": {}
        },
        "ASA": {
            "hourly_rate": 6.5,
            "brands": {}
        },
        "PP": {
            "hourly_rate": 6.0,
            "brands": {}
        },
        "TPU": {
            "hourly_rate": 7.0,
            "brands": {}
        },
        "NYLON": {
            "hourly_rate": 8.0,
            "brands": {}
        },
        "PA": {
            "hourly_rate": 8.0,
            "brands": {}
        },
        "PC": {
            "hourly_rate": 9.0,
            "brands": {}
        },
        "POLYCARBONATE": {
            "hourly_rate": 9.0,
            "brands": {}
        }
    },
    "energy": {
        "cost_per_kwh": 0.80,
        "printer_power_watts": 130.0,
        "preheat_time_minutes": 5.0,
        "preheat_power_watts": 200.0
    },
    "pricing": {
        "margin_percent": 10.0,
        "vat_percent": 23.0,
        "min_price": 0.0,
        "round_to": 0.05
    },
    "advanced": {
        "setup_fee": 0.0,
        "postprocess_rate_per_hour": 0.0,
        "risk_percent": 0.0,
        "packaging_cost": 0.0,
        "shipping_cost": 0.0
    },
    "preferences": {
        "language": "PL",
        "currency": "PLN"
    }
}


class ConfigManager:
    """Manages configuration loading and saving."""

    @staticmethod
    def load_config() -> Dict:
        """Load configuration from file or return defaults."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Check if migration is needed
                    needs_migration = ConfigManager._needs_migration(config)
                    # Migrate old structure to new structure with brands
                    config = ConfigManager._migrate_config(config)
                    # Merge with defaults to ensure all keys exist
                    merged_config = ConfigManager._merge_configs(DEFAULT_CONFIG.copy(), config)
                    # Sync brands from brands.json to remove deleted brands
                    merged_config = ConfigManager._sync_brands_from_inventory(merged_config)
                    # Save migrated config if migration was performed
                    if needs_migration:
                        ConfigManager.save_config(merged_config)
                    return merged_config
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    @staticmethod
    def _sync_brands_from_inventory(config: Dict) -> Dict:
        """Sync brands from inventory (brands.json) to config, removing deleted brands."""
        try:
            from utils.db_handler import load_brands
            inventory_brands = load_brands()
            inventory_brand_names = {brand['name'].upper() for brand in inventory_brands}
            
            # For each material, sync brands with inventory
            for material_name, material_data in config.get("materials", {}).items():
                if "brands" not in material_data:
                    material_data["brands"] = {}
                
                # Remove brands that are no longer in inventory
                brands_to_remove = []
                for brand_name in material_data["brands"].keys():
                    if brand_name.upper() not in inventory_brand_names:
                        brands_to_remove.append(brand_name)
                
                for brand_name in brands_to_remove:
                    del material_data["brands"][brand_name]
                
                # Add missing brands from inventory with default price (0.0)
                existing_brands = {brand.upper() for brand in material_data["brands"].keys()}
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
        except Exception as e:
            print(f"Error syncing brands from inventory: {e}")
        
        return config
    
    @staticmethod
    def _needs_migration(config: Dict) -> bool:
        """Check if config needs migration from old structure to new structure."""
        if "materials" in config:
            for material_name, material_data in config["materials"].items():
                if isinstance(material_data, dict) and "price_per_kg" in material_data and "brands" not in material_data:
                    return True
        return False
    
    @staticmethod
    def _migrate_config(config: Dict) -> Dict:
        """
        Migrate old config structure (without brands) to new structure (with brands).
        
        Old structure: materials.MATERIAL.price_per_kg
        New structure: materials.MATERIAL.brands.BRAND.price_per_kg
        """
        if "materials" in config:
            for material_name, material_data in config["materials"].items():
                # Check if old structure (has price_per_kg directly)
                if isinstance(material_data, dict) and "price_per_kg" in material_data and "brands" not in material_data:
                    # Migrate: move price_per_kg to brands (but don't add default brands)
                    old_price = material_data.get("price_per_kg", 139.0)
                    hourly_rate = material_data.get("hourly_rate", 5.0)
                    
                    # Replace entire material structure with empty brands
                    # Brands will be synced from brands.json by settings dialog
                    config["materials"][material_name] = {
                        "hourly_rate": hourly_rate,
                        "brands": {}
                    }
        return config

    @staticmethod
    def save_config(config: Dict):
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    @staticmethod
    def _merge_configs(default: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded config with defaults."""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                default[key] = ConfigManager._merge_configs(default[key], value)
            else:
                default[key] = value
        return default


class PriceCalculator:
    """Core calculation logic for 3D printing price estimation."""

    @staticmethod
    def calculate_material_cost(filament_weight_g: float, material_price_per_kg: float, copies: int = 1) -> float:
        """Calculate material cost based on filament weight and price per kilogram."""
        weight_kg = (filament_weight_g * copies) / 1000.0
        return weight_kg * material_price_per_kg

    @staticmethod
    def calculate_printer_time_cost(
        print_time_hours: float,
        hourly_rate: float,
        preheat_time_minutes: float = 0.0,
        copies: int = 1
    ) -> float:
        """Calculate cost based on printer time usage including preheat."""
        preheat_hours = preheat_time_minutes / 60.0
        total_time = (print_time_hours + preheat_hours) * copies
        return total_time * hourly_rate

    @staticmethod
    def calculate_energy_consumption(
        print_time_hours: float,
        printer_power_watts: float,
        preheat_time_minutes: float = 0.0,
        preheat_power_watts: float = 0.0,
        copies: int = 1
    ) -> float:
        """Calculate energy consumption including preheat."""
        preheat_hours = preheat_time_minutes / 60.0
        print_energy = (print_time_hours * copies) * (printer_power_watts / 1000.0)
        preheat_energy = preheat_hours * (preheat_power_watts / 1000.0) if copies > 0 else 0.0
        return print_energy + preheat_energy

    @staticmethod
    def calculate_energy_cost(energy_consumption_kwh: float, cost_per_kwh: float) -> float:
        """Calculate energy cost for printing."""
        return energy_consumption_kwh * cost_per_kwh

    @staticmethod
    def calculate_postprocess_cost(postprocess_time_hours: float, rate_per_hour: float) -> float:
        """Calculate post-processing cost."""
        return postprocess_time_hours * rate_per_hour

    @staticmethod
    def apply_risk_factor(base_cost: float, risk_percent: float) -> float:
        """Apply risk factor to account for failed prints."""
        return base_cost * (1 + risk_percent / 100.0)

    @staticmethod
    def round_price(price: float, round_to: float = 0.05) -> float:
        """Round price to nearest increment (e.g., 0.05 for 5 groszy)."""
        if round_to <= 0:
            return price
        return round(price / round_to) * round_to

    @staticmethod
    def calculate_price(
        filament_weight_g: float,
        material_price_per_kg: float,
        print_time_hours: float,
        hourly_rate: float,
        energy_consumption_kwh: float,
        cost_per_kwh: float,
        margin_percent: float,
        copies: int = 1,
        setup_fee: float = 0.0,
        postprocess_time_hours: float = 0.0,
        postprocess_rate_per_hour: float = 0.0,
        risk_percent: float = 0.0,
        packaging_cost: float = 0.0,
        shipping_cost: float = 0.0,
        min_price: float = 0.0,
        vat_percent: float = 0.0,
        round_to: float = 0.05
    ) -> Dict[str, float]:
        """
        Calculate complete price breakdown for 3D printing service.

        Returns:
            Dict[str, float]: Dictionary containing complete cost breakdown.
        """
        # Base costs
        material_cost = PriceCalculator.calculate_material_cost(
            filament_weight_g, material_price_per_kg, copies
        )
        time_cost = PriceCalculator.calculate_printer_time_cost(
            print_time_hours, hourly_rate, 0.0, copies
        )
        energy_cost = PriceCalculator.calculate_energy_cost(energy_consumption_kwh, cost_per_kwh)
        postprocess_cost = PriceCalculator.calculate_postprocess_cost(
            postprocess_time_hours, postprocess_rate_per_hour
        )

        # Subtotal before risk
        subtotal = material_cost + time_cost + energy_cost + postprocess_cost + setup_fee

        # Apply risk factor
        risk_adjusted_cost = PriceCalculator.apply_risk_factor(subtotal, risk_percent)
        risk_amount = risk_adjusted_cost - subtotal

        # Apply margin
        margin_amount = risk_adjusted_cost * (margin_percent / 100.0)
        price_before_packaging = risk_adjusted_cost + margin_amount

        # Add packaging and shipping
        price_before_vat = price_before_packaging + packaging_cost + shipping_cost

        # Apply minimum price
        if min_price > 0 and price_before_vat < min_price:
            price_before_vat = min_price

        # Round price
        price_before_vat = PriceCalculator.round_price(price_before_vat, round_to)

        # Calculate VAT
        vat_amount = price_before_vat * (vat_percent / 100.0) if vat_percent > 0 else 0.0
        final_price = price_before_vat + vat_amount

        return {
            'material_cost': material_cost,
            'time_cost': time_cost,
            'energy_cost': energy_cost,
            'postprocess_cost': postprocess_cost,
            'setup_fee': setup_fee,
            'subtotal': subtotal,
            'risk_amount': risk_amount,
            'risk_adjusted_cost': risk_adjusted_cost,
            'margin_amount': margin_amount,
            'price_before_packaging': price_before_packaging,
            'packaging_cost': packaging_cost,
            'shipping_cost': shipping_cost,
            'price_before_vat': price_before_vat,
            'vat_amount': vat_amount,
            'final_price': final_price
        }

