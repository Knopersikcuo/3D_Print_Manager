"""
Database handler for PrintManager application.
Manages JSON-based storage for filaments, brands, and print history.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# File paths
BRANDS_FILE = os.path.join(DATA_DIR, "brands.json")
FILAMENTS_FILE = os.path.join(DATA_DIR, "filaments.json")
PRINTS_FILE = os.path.join(DATA_DIR, "prints.json")


def _ensure_data_dir():
    """Ensure data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(file_path: str, default: Dict) -> Dict:
    """Load JSON file or return default if file doesn't exist."""
    _ensure_data_dir()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return default
    return default


def _save_json(file_path: str, data: Dict):
    """Save data to JSON file."""
    _ensure_data_dir()
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        raise


# Brand functions
def load_brands() -> List[Dict]:
    """Load all brands from storage."""
    data = _load_json(BRANDS_FILE, {"brands": []})
    return data.get("brands", [])


def get_all_brands() -> List[str]:
    """Get list of all brand names."""
    brands = load_brands()
    return [brand["name"] for brand in brands]


def get_spool_weight(brand_name: str) -> int:
    """Get spool weight for a specific brand."""
    brands = load_brands()
    for brand in brands:
        if brand["name"] == brand_name:
            return brand.get("spool_weight", 150)
    return 150  # Default spool weight


def add_brand(name: str, spool_weight: int):
    """
    Add a new brand to storage.
    
    Args:
        name: Brand name
        spool_weight: Spool weight in grams
        
    Raises:
        ValueError: If brand with same name already exists
    """
    brands = load_brands()
    
    # Check if brand already exists
    for brand in brands:
        if brand["name"].upper() == name.upper():
            raise ValueError(f"Marka '{name}' już istnieje.")
    
    # Add new brand
    new_brand = {
        "id": str(uuid.uuid4()),
        "name": name.upper(),
        "spool_weight": spool_weight,
        "created_at": datetime.now().isoformat()
    }
    
    brands.append(new_brand)
    _save_json(BRANDS_FILE, {"brands": brands})


def get_brand_by_id(brand_id: str) -> Optional[Dict]:
    """
    Get brand by ID.
    
    Args:
        brand_id: Brand ID
        
    Returns:
        Brand dict or None if not found
    """
    brands = load_brands()
    for brand in brands:
        if brand.get("id") == brand_id:
            return brand
    return None


def update_brand(brand_id: str, name: str, spool_weight: int):
    """
    Update an existing brand.
    
    Args:
        brand_id: Brand ID to update
        name: New brand name
        spool_weight: New spool weight in grams
        
    Raises:
        ValueError: If brand not found or brand with same name already exists
    """
    brands = load_brands()
    brand_index = None
    
    # Find the brand
    for i, brand in enumerate(brands):
        if brand.get("id") == brand_id:
            brand_index = i
            break
    
    if brand_index is None:
        raise ValueError("Marka nie została znaleziona.")
    
    # Check if new name conflicts with existing brand (excluding current brand)
    for i, brand in enumerate(brands):
        if i != brand_index and brand["name"].upper() == name.upper():
            raise ValueError(f"Marka '{name}' już istnieje.")
    
    # Update brand
    brands[brand_index].update({
        "name": name.upper(),
        "spool_weight": spool_weight,
        "updated_at": datetime.now().isoformat()
    })
    
    _save_json(BRANDS_FILE, {"brands": brands})


def delete_brand(brand_id: str) -> bool:
    """
    Delete a brand from storage.
    
    Args:
        brand_id: Brand ID to delete
        
    Returns:
        True if deleted successfully, False if not found
        
    Raises:
        ValueError: If brand is used by filaments
    """
    brands = load_brands()
    
    # Find brand to delete
    brand_to_delete = None
    for brand in brands:
        if brand.get("id") == brand_id:
            brand_to_delete = brand
            break
    
    if not brand_to_delete:
        return False
    
    brand_name = brand_to_delete["name"]
    
    # Check if brand is used by any filament
    filaments = load_filaments()
    for filament in filaments:
        if filament.get("brand", "").upper() == brand_name.upper():
            raise ValueError(
                f"Nie można usunąć marki '{brand_name}', ponieważ jest używana przez filamenty."
            )
    
    # Remove brand
    brands = [b for b in brands if b.get("id") != brand_id]
    _save_json(BRANDS_FILE, {"brands": brands})
    
    return True


# Filament functions
def load_filaments() -> List[Dict]:
    """Load all filaments from storage."""
    data = _load_json(FILAMENTS_FILE, {"filaments": []})
    return data.get("filaments", [])


def get_filament_by_id(filament_id: str) -> Optional[Dict]:
    """Get filament by ID."""
    filaments = load_filaments()
    for filament in filaments:
        if filament["id"] == filament_id:
            return filament
    return None


def add_filament(
    color: str,
    brand: str,
    filament_type: str,
    initial_weight: int,
    without_spool: bool = False
):
    """
    Add a new filament to storage.
    
    Args:
        color: Color hex code (e.g., "#FF0000")
        brand: Brand name
        filament_type: Type of filament (PLA, PETG, etc.)
        initial_weight: Initial weight in grams
        without_spool: If True, initial_weight is net weight (without spool)
        
    Raises:
        ValueError: If weight is invalid
    """
    spool_weight = get_spool_weight(brand)
    
    if without_spool:
        # Weight is already net (without spool)
        net_weight = initial_weight
        total_weight = initial_weight
    else:
        # Weight includes spool, calculate net weight
        net_weight = initial_weight - spool_weight
        total_weight = initial_weight
        
        if net_weight <= 0:
            raise ValueError(
                f"Waga początkowa ({initial_weight}g) jest zbyt mała.\n"
                f"Waga szpuli dla marki {brand} to {spool_weight}g.\n"
                f"Waga netto: {net_weight}g"
            )
    
    new_filament = {
        "id": str(uuid.uuid4()),
        "color": color,
        "brand": brand.upper(),
        "type": filament_type.upper(),
        "initial_weight": net_weight,
        "current_weight": net_weight,
        "spool_weight": spool_weight if not without_spool else 0,
        "created_at": datetime.now().isoformat()
    }
    
    filaments = load_filaments()
    filaments.append(new_filament)
    _save_json(FILAMENTS_FILE, {"filaments": filaments})


def update_filament(
    filament_id: str,
    color: str,
    brand: str,
    filament_type: str,
    initial_weight: int,
    without_spool: bool = False
):
    """
    Update an existing filament.
    
    Args:
        filament_id: Filament ID
        color: Color hex code
        brand: Brand name
        filament_type: Type of filament
        initial_weight: Initial weight in grams
        without_spool: If True, initial_weight is net weight
        
    Raises:
        ValueError: If filament not found or weight is invalid
    """
    filaments = load_filaments()
    filament_index = None
    
    for i, filament in enumerate(filaments):
        if filament["id"] == filament_id:
            filament_index = i
            break
    
    if filament_index is None:
        raise ValueError("Filament nie został znaleziony.")
    
    spool_weight = get_spool_weight(brand)
    
    if without_spool:
        net_weight = initial_weight
    else:
        net_weight = initial_weight - spool_weight
        if net_weight <= 0:
            raise ValueError(
                f"Waga początkowa ({initial_weight}g) jest zbyt mała.\n"
                f"Waga szpuli dla marki {brand} to {spool_weight}g.\n"
                f"Waga netto: {net_weight}g"
            )
    
    # Calculate current weight difference
    old_filament = filaments[filament_index]
    weight_difference = net_weight - old_filament["initial_weight"]
    new_current_weight = old_filament["current_weight"] + weight_difference
    
    # Update filament
    filaments[filament_index].update({
        "color": color,
        "brand": brand.upper(),
        "type": filament_type.upper(),
        "initial_weight": net_weight,
        "current_weight": max(0, new_current_weight),  # Ensure non-negative
        "spool_weight": spool_weight if not without_spool else 0
    })
    
    _save_json(FILAMENTS_FILE, {"filaments": filaments})


def delete_filament(filament_id: str) -> bool:
    """
    Delete a filament from storage.
    
    Args:
        filament_id: Filament ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    filaments = load_filaments()
    original_count = len(filaments)
    
    filaments = [f for f in filaments if f["id"] != filament_id]
    
    if len(filaments) < original_count:
        _save_json(FILAMENTS_FILE, {"filaments": filaments})
        return True
    return False


def update_filament_weight(filament_id: str, weight_used: int) -> bool:
    """
    Subtract weight from filament's current weight.
    
    Args:
        filament_id: Filament ID
        weight_used: Weight to subtract in grams
        
    Returns:
        True if successful, False if filament not found or insufficient weight
    """
    filaments = load_filaments()
    
    for i, filament in enumerate(filaments):
        if filament["id"] == filament_id:
            if filament["current_weight"] < weight_used:
                return False
            
            filaments[i]["current_weight"] -= weight_used
            _save_json(FILAMENTS_FILE, {"filaments": filaments})
            return True
    
    return False


# Print history functions
def load_prints() -> List[Dict]:
    """Load all prints from storage."""
    data = _load_json(PRINTS_FILE, {"prints": []})
    return data.get("prints", [])


def add_print(filament_id: str, print_name: str, weight_used: int, price: Optional[float] = None, gcode_file: Optional[str] = None):
    """
    Add a print record to history.
    
    Args:
        filament_id: Filament ID used for print
        print_name: Name of the print
        weight_used: Weight used in grams
        price: Optional price of the print
        gcode_file: Optional G-code filename
        
    Raises:
        ValueError: If filament not found or insufficient weight
    """
    # Verify filament exists and has enough weight
    filament = get_filament_by_id(filament_id)
    if not filament:
        raise ValueError("Filament nie został znaleziony.")
    
    if filament["current_weight"] < weight_used:
        raise ValueError(
            f"Niewystarczająca waga dostępna.\n"
            f"Dostępna: {filament['current_weight']} g\n"
            f"Żądana: {weight_used} g"
        )
    
    # Subtract weight from filament
    if not update_filament_weight(filament_id, weight_used):
        raise ValueError("Nie udało się zaktualizować wagi filamentu.")
    
    # Add print record
    new_print = {
        "id": str(uuid.uuid4()),
        "filament_id": filament_id,
        "print_name": print_name,
        "weight_used": weight_used,
        "price": price,
        "gcode_file": gcode_file,
        "timestamp": datetime.now().isoformat()
    }
    
    prints = load_prints()
    prints.append(new_print)
    _save_json(PRINTS_FILE, {"prints": prints})


def get_filament_history(filament_id: str) -> List[Dict]:
    """
    Get print history for a specific filament.
    
    Args:
        filament_id: Filament ID
        
    Returns:
        List of print records, sorted by timestamp (newest first)
    """
    prints = load_prints()
    history = [p for p in prints if p["filament_id"] == filament_id]
    
    # Sort by timestamp (newest first)
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return history


def get_all_prints() -> List[Dict]:
    """
    Get all print records.
    
    Returns:
        List of all print records, sorted by timestamp (newest first)
    """
    prints = load_prints()
    prints.sort(key=lambda x: x["timestamp"], reverse=True)
    return prints


def delete_print(print_id: str, restore_weight: bool = True) -> bool:
    """
    Delete a print record from history and optionally restore weight to filament.
    
    Args:
        print_id: Print record ID to delete
        restore_weight: If True, restore weight to filament's current weight
        
    Returns:
        True if deleted successfully, False if not found
    """
    prints = load_prints()
    print_to_delete = None
    
    # Find the print record
    for p in prints:
        if p["id"] == print_id:
            print_to_delete = p
            break
    
    if not print_to_delete:
        return False
    
    # Restore weight to filament if requested
    if restore_weight:
        filament_id = print_to_delete.get("filament_id")
        weight_used = print_to_delete.get("weight_used", 0)
        
        if filament_id and weight_used > 0:
            filaments = load_filaments()
            for i, filament in enumerate(filaments):
                if filament["id"] == filament_id:
                    filaments[i]["current_weight"] += weight_used
                    _save_json(FILAMENTS_FILE, {"filaments": filaments})
                    break
    
    # Remove print record
    prints = [p for p in prints if p["id"] != print_id]
    _save_json(PRINTS_FILE, {"prints": prints})
    
    return True


def get_print_by_id(print_id: str) -> Optional[Dict]:
    """
    Get print record by ID.
    
    Args:
        print_id: Print record ID
        
    Returns:
        Print record dict or None if not found
    """
    prints = load_prints()
    for p in prints:
        if p["id"] == print_id:
            return p
    return None


def update_print(
    print_id: str,
    print_name: Optional[str] = None,
    filament_id: Optional[str] = None,
    weight_used: Optional[int] = None,
    price: Optional[float] = None
) -> bool:
    """
    Update an existing print record.
    
    Args:
        print_id: Print record ID to update
        print_name: New print name (optional)
        filament_id: New filament ID (optional)
        weight_used: New weight used in grams (optional)
        price: New price (optional)
        
    Returns:
        True if updated successfully, False if not found
        
    Raises:
        ValueError: If filament not found or insufficient weight
    """
    prints = load_prints()
    print_index = None
    
    # Find the print record
    for i, p in enumerate(prints):
        if p["id"] == print_id:
            print_index = i
            break
    
    if print_index is None:
        return False
    
    old_print = prints[print_index].copy()
    old_filament_id = old_print.get("filament_id")
    old_weight_used = old_print.get("weight_used", 0)
    
    # Determine new values
    new_filament_id = filament_id if filament_id is not None else old_filament_id
    new_weight_used = weight_used if weight_used is not None else old_weight_used
    new_print_name = print_name if print_name is not None else old_print.get("print_name")
    new_price = price if price is not None else old_print.get("price")
    
    # Handle weight changes
    if old_filament_id != new_filament_id or old_weight_used != new_weight_used:
        # Restore old weight to old filament
        if old_filament_id and old_weight_used > 0:
            filaments = load_filaments()
            for i, filament in enumerate(filaments):
                if filament["id"] == old_filament_id:
                    filaments[i]["current_weight"] += old_weight_used
                    _save_json(FILAMENTS_FILE, {"filaments": filaments})
                    break
        
        # Verify new filament exists and has enough weight
        new_filament = get_filament_by_id(new_filament_id)
        if not new_filament:
            # Restore old state if new filament not found
            if old_filament_id and old_weight_used > 0:
                filaments = load_filaments()
                for i, filament in enumerate(filaments):
                    if filament["id"] == old_filament_id:
                        filaments[i]["current_weight"] -= old_weight_used
                        _save_json(FILAMENTS_FILE, {"filaments": filaments})
                        break
            raise ValueError("Filament nie został znaleziony.")
        
        # Check if new filament has enough weight
        available_weight = new_filament["current_weight"]
        if old_filament_id == new_filament_id:
            # Same filament - account for restored weight
            available_weight += old_weight_used
        
        if available_weight < new_weight_used:
            # Restore old state if insufficient weight
            if old_filament_id and old_weight_used > 0:
                filaments = load_filaments()
                for i, filament in enumerate(filaments):
                    if filament["id"] == old_filament_id:
                        filaments[i]["current_weight"] -= old_weight_used
                        _save_json(FILAMENTS_FILE, {"filaments": filaments})
                        break
            raise ValueError(
                f"Niewystarczająca waga dostępna.\n"
                f"Dostępna: {available_weight} g\n"
                f"Żądana: {new_weight_used} g"
            )
        
        # Subtract new weight from new filament
        if not update_filament_weight(new_filament_id, new_weight_used):
            # Restore old state if update failed
            if old_filament_id and old_weight_used > 0:
                filaments = load_filaments()
                for i, filament in enumerate(filaments):
                    if filament["id"] == old_filament_id:
                        filaments[i]["current_weight"] -= old_weight_used
                        _save_json(FILAMENTS_FILE, {"filaments": filaments})
                        break
            raise ValueError("Nie udało się zaktualizować wagi filamentu.")
    
    # Update print record
    prints[print_index].update({
        "print_name": new_print_name,
        "filament_id": new_filament_id,
        "weight_used": new_weight_used,
        "price": new_price
    })
    
    _save_json(PRINTS_FILE, {"prints": prints})
    return True

