"""
Translation system for the application.
Supports Polish (PL) and English (EN) languages.
Also includes currency management.
"""

import json
import os
from typing import Dict, Callable, List

# Get script directory for preferences file
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFERENCES_FILE = os.path.join(SCRIPT_DIR, "data", "preferences.json")

# Current language state
_current_language = "PL"

# Current currency state
_current_currency = "PLN"

# List of callbacks to notify when language changes
_language_change_callbacks: List[Callable] = []

# List of callbacks to notify when currency changes
_currency_change_callbacks: List[Callable] = []

# Supported currencies with symbols and exchange rates (relative to PLN)
CURRENCIES: Dict[str, Dict] = {
    "PLN": {"symbol": "zł", "name": "Polish Zloty", "rate": 1.0, "position": "after"},
    "EUR": {"symbol": "€", "name": "Euro", "rate": 0.23, "position": "before"},
    "USD": {"symbol": "$", "name": "US Dollar", "rate": 0.25, "position": "before"},
    "GBP": {"symbol": "£", "name": "British Pound", "rate": 0.20, "position": "before"},
}

# Translation dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # Main window
    "settings": {"PL": "⚙ Ustawienia", "EN": "⚙ Settings"},
    "calculator": {"PL": "📊 Kalkulator", "EN": "📊 Calculator"},
    "inventory": {"PL": "📦 Magazyn", "EN": "📦 Inventory"},
    "history": {"PL": "📋 Historia", "EN": "📋 History"},
    
    # Calculator tab
    "gcode_files": {"PL": "Pliki G-code", "EN": "G-code Files"},
    "add_files": {"PL": "➕ Dodaj pliki", "EN": "➕ Add Files"},
    "remove_selected": {"PL": "🗑️ Usuń zaznaczone", "EN": "🗑️ Remove Selected"},
    "clear_all": {"PL": "🧹 Wyczyść wszystko", "EN": "🧹 Clear All"},
    "drag_drop_hint": {"PL": "Przeciągnij i upuść pliki G-code tutaj...", "EN": "Drag and drop G-code files here..."},
    "filament_selection": {"PL": "Wybór filamentu", "EN": "Filament Selection"},
    "select_filament": {"PL": "-- Wybierz filament --", "EN": "-- Select filament --"},
    "no_filament": {"PL": "-- Brak filamentu --", "EN": "-- No filament --"},
    "copies": {"PL": "Liczba kopii:", "EN": "Copies:"},
    "postprocess_time": {"PL": "Czas postprocessu (h):", "EN": "Post-process time (h):"},
    "calculate": {"PL": "📊 Oblicz cenę", "EN": "📊 Calculate Price"},
    "execute_print": {"PL": "✅ Zapisz wydruk", "EN": "✅ Save Print"},
    "price_summary": {"PL": "Podsumowanie ceny", "EN": "Price Summary"},
    "material_cost": {"PL": "Koszt materiału:", "EN": "Material cost:"},
    "time_cost": {"PL": "Koszt czasu:", "EN": "Time cost:"},
    "energy_cost": {"PL": "Koszt energii:", "EN": "Energy cost:"},
    "postprocess_cost": {"PL": "Koszt postprocessu:", "EN": "Post-process cost:"},
    "setup_fee": {"PL": "Opłata przygotowawcza:", "EN": "Setup fee:"},
    "subtotal": {"PL": "Suma częściowa:", "EN": "Subtotal:"},
    "risk_margin": {"PL": "Ryzyko:", "EN": "Risk:"},
    "net_price": {"PL": "Cena netto:", "EN": "Net price:"},
    "vat": {"PL": "VAT:", "EN": "VAT:"},
    "final_price": {"PL": "CENA KOŃCOWA", "EN": "FINAL PRICE"},
    "base_costs_title": {"PL": "📦 KOSZTY BAZOWE", "EN": "📦 BASE COSTS"},
    "additions_title": {"PL": "📊 DODATKI", "EN": "📊 ADDITIONS"},
    "final_title": {"PL": "💰 PODSUMOWANIE", "EN": "💰 FINAL"},
    "print_details": {"PL": "Szczegóły wydruku", "EN": "Print Details"},
    "total_time": {"PL": "Czas druku (h):", "EN": "Print time (h):"},
    "total_weight": {"PL": "Całkowita waga:", "EN": "Total weight:"},
    "material_type": {"PL": "Typ materiału:", "EN": "Material type:"},
    "files_count": {"PL": "Liczba plików:", "EN": "Files count:"},
    "available_weight": {"PL": "Dostępna waga:", "EN": "Available weight:"},
    "filament_weight": {"PL": "Filament (g):", "EN": "Filament (g):"},
    "energy_kwh": {"PL": "Energia (kWh):", "EN": "Energy (kWh):"},
    "load_btn": {"PL": "▶ Załaduj", "EN": "▶ Load"},
    "select_btn": {"PL": "📁 Wybierz", "EN": "📁 Select"},
    "clear_btn": {"PL": "🗑 Wyczyść", "EN": "🗑 Clear"},
    "placeholder_weight": {"PL": "np. 150", "EN": "e.g. 150"},
    "placeholder_time": {"PL": "np. 5.5", "EN": "e.g. 5.5"},
    
    # Inventory tab
    "add_filament": {"PL": "➕ Dodaj filament", "EN": "➕ Add Filament"},
    "edit": {"PL": "✏️ Edytuj", "EN": "✏️ Edit"},
    "delete": {"PL": "🗑️ Usuń", "EN": "🗑️ Delete"},
    "filament_history": {"PL": "📊 Historia", "EN": "📊 History"},
    "brands": {"PL": "🏷️ Marki", "EN": "🏷️ Brands"},
    "color": {"PL": "Kolor", "EN": "Color"},
    "brand": {"PL": "Marka", "EN": "Brand"},
    "initial_weight": {"PL": "Waga początkowa (netto, g)", "EN": "Initial Weight (net, g)"},
    "current_weight": {"PL": "Waga aktualna (netto, g)", "EN": "Current Weight (net, g)"},
    
    # History tab
    "print_name": {"PL": "Nazwa wydruku", "EN": "Print Name"},
    "filament": {"PL": "Filament", "EN": "Filament"},
    "weight_used": {"PL": "Zużyta waga (g)", "EN": "Weight Used (g)"},
    "price": {"PL": "Cena", "EN": "Price"},
    "date": {"PL": "Data", "EN": "Date"},
    "edit_print_title": {"PL": "Edytuj wydruk", "EN": "Edit Print"},
    "edit_print_btn": {"PL": "✏️ Edytuj wydruk", "EN": "✏️ Edit Print"},
    "filter_by_filament": {"PL": "Filtruj po filamencie:", "EN": "Filter by filament:"},
    "date_from": {"PL": "Od:", "EN": "From:"},
    "date_to": {"PL": "Do:", "EN": "To:"},
    "all_filaments": {"PL": "-- Wszystkie filamenty --", "EN": "-- All filaments --"},
    "total_weight_sum": {"PL": "Suma wagi:", "EN": "Total weight:"},
    "total_price_sum": {"PL": "Suma cen:", "EN": "Total price:"},
    "clear_filters": {"PL": "🔄 Wyczyść filtry", "EN": "🔄 Clear Filters"},
    
    # Multicolor support
    "select_filaments_multicolor": {"PL": "Wybierz filamenty dla druku multicolor", "EN": "Select Filaments for Multicolor Print"},
    "multicolor_info": {"PL": "Wykryto druk multicolor z {count} filamentami. Wybierz filament dla każdej wagi:", "EN": "Detected multicolor print with {count} filaments. Select filament for each weight:"},
    "filament_weight_label": {"PL": "Filament {num} ({weight} g):", "EN": "Filament {num} ({weight} g):"},
    "select_filament_for_weight": {"PL": "Proszę wybrać filament dla wagi {num}.", "EN": "Please select filament for weight {num}."},
    "not_enough_filament_for_weight": {"PL": "Niewystarczająca waga dla filamentu {num}.\nWymagana: {weight} g\nDostępna ({brand}): {available} g", "EN": "Insufficient weight for filament {num}.\nRequired: {weight} g\nAvailable ({brand}): {available} g"},
    "multicolor_selected": {"PL": "Wybrano multicolor", "EN": "Multicolor selected"},
    "ok": {"PL": "OK", "EN": "OK"},
    "cancel": {"PL": "Anuluj", "EN": "Cancel"},
    
    # Settings dialog
    "settings_title": {"PL": "Ustawienia", "EN": "Settings"},
    "materials_section": {"PL": "Materiały", "EN": "Materials"},
    "materials": {"PL": "Materiały", "EN": "Materials"},
    "hourly_rate": {"PL": "Stawka godzinowa:", "EN": "Hourly rate:"},
    "hourly_rate_label": {"PL": "Stawka godzinowa:", "EN": "Hourly rate:"},
    "brands_label": {"PL": "Marki:", "EN": "Brands:"},
    "energy_section": {"PL": "Energia", "EN": "Energy"},
    "energy": {"PL": "Energia", "EN": "Energy"},
    "cost_per_kwh": {"PL": "Koszt kWh:", "EN": "Cost per kWh:"},
    "cost_per_kwh_label": {"PL": "Koszt kWh:", "EN": "Cost per kWh:"},
    "printer_power": {"PL": "Moc drukarki:", "EN": "Printer power:"},
    "printer_power_label": {"PL": "Moc drukarki:", "EN": "Printer power:"},
    "preheat_time": {"PL": "Czas nagrzewania:", "EN": "Preheat time:"},
    "preheat_time_label": {"PL": "Czas nagrzewania:", "EN": "Preheat time:"},
    "preheat_power": {"PL": "Moc nagrzewania:", "EN": "Preheat power:"},
    "preheat_power_label": {"PL": "Moc nagrzewania:", "EN": "Preheat power:"},
    "pricing_section": {"PL": "Cennik", "EN": "Pricing"},
    "pricing": {"PL": "Cennik", "EN": "Pricing"},
    "margin": {"PL": "Marża:", "EN": "Margin:"},
    "margin_label": {"PL": "Marża:", "EN": "Margin:"},
    "vat_label": {"PL": "VAT:", "EN": "VAT:"},
    "min_price": {"PL": "Cena minimalna:", "EN": "Minimum price:"},
    "min_price_label": {"PL": "Cena minimalna:", "EN": "Minimum price:"},
    "round_to": {"PL": "Zaokrąglanie do:", "EN": "Round to:"},
    "round_to_label": {"PL": "Zaokrąglanie do:", "EN": "Round to:"},
    "advanced_section": {"PL": "Zaawansowane", "EN": "Advanced"},
    "advanced": {"PL": "Zaawansowane", "EN": "Advanced"},
    "setup_fee_label": {"PL": "Opłata przygotowawcza:", "EN": "Setup fee:"},
    "postprocess_rate": {"PL": "Stawka postprocessu:", "EN": "Post-process rate:"},
    "postprocess_rate_label": {"PL": "Stawka postprocessu:", "EN": "Post-process rate:"},
    "risk_factor": {"PL": "Współczynnik ryzyka:", "EN": "Risk factor:"},
    "risk_label": {"PL": "Współczynnik ryzyka:", "EN": "Risk factor:"},
    "packaging_cost": {"PL": "Koszt pakowania:", "EN": "Packaging cost:"},
    "packaging_label": {"PL": "Koszt pakowania:", "EN": "Packaging cost:"},
    "shipping_cost": {"PL": "Koszt wysyłki:", "EN": "Shipping cost:"},
    "shipping_label": {"PL": "Koszt wysyłki:", "EN": "Shipping cost:"},
    "settings_saved": {"PL": "Ustawienia zostały zapisane.", "EN": "Settings have been saved."},
    "currency_per_hour": {"PL": "zł/h", "EN": "zł/h"},
    "currency_per_kg": {"PL": "zł/kg", "EN": "zł/kg"},
    "currency_per_kwh": {"PL": "zł/kWh", "EN": "zł/kWh"},
    "currency_symbol": {"PL": "zł", "EN": "zł"},
    
    # Add/Edit Filament dialogs
    "add_filament_title": {"PL": "Dodaj filament", "EN": "Add Filament"},
    "edit_filament_title": {"PL": "Edytuj filament", "EN": "Edit Filament"},
    "color_label": {"PL": "Kolor:", "EN": "Color:"},
    "brand_label": {"PL": "Marka:", "EN": "Brand:"},
    "filament_type": {"PL": "Typ filamentu:", "EN": "Filament type:"},
    "without_spool": {"PL": "Waga bez szpuli (waga netto)", "EN": "Weight without spool (net weight)"},
    "weight_with_spool": {"PL": "Waga początkowa (ze szpulą, g):", "EN": "Initial weight (with spool, g):"},
    "weight_without_spool": {"PL": "Waga początkowa (bez szpuli, g):", "EN": "Initial weight (without spool, g):"},
    "spool_weight_info": {"PL": "ℹ️ Waga szpuli dla marki {brand}: {weight}g (zostanie automatycznie odjęta)", "EN": "ℹ️ Spool weight for {brand}: {weight}g (will be automatically subtracted)"},
    "spool_weight_info_no_sub": {"PL": "ℹ️ Waga szpuli dla marki {brand}: {weight}g (nie będzie odejmowana)", "EN": "ℹ️ Spool weight for {brand}: {weight}g (will not be subtracted)"},
    "net_weight_display": {"PL": "📊 Waga netto filamentu (bez szpuli): {weight}g", "EN": "📊 Net filament weight (without spool): {weight}g"},
    "net_weight_display_no_spool": {"PL": "📊 Waga netto filamentu: {weight}g (bez szpuli)", "EN": "📊 Net filament weight: {weight}g (without spool)"},
    "net_weight_warning": {"PL": "⚠️ Waga netto: {weight}g (waga zbyt mała!)", "EN": "⚠️ Net weight: {weight}g (weight too small!)"},
    "current_net_weight": {"PL": "Aktualna waga netto: {weight} g", "EN": "Current net weight: {weight} g"},
    "save_changes": {"PL": "Zapisz zmiany", "EN": "Save Changes"},
    "select_color": {"PL": "Wybierz kolor", "EN": "Select Color"},
    "brand_required": {"PL": "Marka jest wymagana.", "EN": "Brand is required."},
    "weight_too_small": {"PL": "Waga początkowa ({total}g) jest zbyt mała.\nWaga szpuli dla marki {brand} to {spool}g.\nWaga netto: {net}g", "EN": "Initial weight ({total}g) is too small.\nSpool weight for {brand} is {spool}g.\nNet weight: {net}g"},
    "add_filament_error": {"PL": "Nie udało się dodać filamentu:\n{error}", "EN": "Failed to add filament:\n{error}"},
    "update_filament_error": {"PL": "Nie udało się zaktualizować filamentu:\n{error}", "EN": "Failed to update filament:\n{error}"},
    
    # Brands dialog
    "brands_title": {"PL": "Zarządzanie markami", "EN": "Manage Brands"},
    "brands_title_full": {"PL": "Zarządzanie markami filamentów", "EN": "Filament Brands Management"},
    "add_new_brand": {"PL": "Dodaj nową markę:", "EN": "Add new brand:"},
    "name_label": {"PL": "Nazwa:", "EN": "Name:"},
    "spool_weight": {"PL": "Waga szpuli (g):", "EN": "Spool weight (g):"},
    "add_btn": {"PL": "➕ Dodaj", "EN": "➕ Add"},
    "edit_btn": {"PL": "✏️ Edytuj", "EN": "✏️ Edit"},
    "delete_btn": {"PL": "🗑️ Usuń", "EN": "🗑️ Delete"},
    "close": {"PL": "Zamknij", "EN": "Close"},
    "brand_name_required": {"PL": "Nazwa marki jest wymagana.", "EN": "Brand name is required."},
    "brand_added": {"PL": "Marka '{name}' została dodana.", "EN": "Brand '{name}' has been added."},
    "brand_updated": {"PL": "Marka '{name}' została zaktualizowana.", "EN": "Brand '{name}' has been updated."},
    "brand_deleted": {"PL": "Marka '{name}' została usunięta.", "EN": "Brand '{name}' has been deleted."},
    "add_brand_error": {"PL": "Nie udało się dodać marki:\n{error}", "EN": "Failed to add brand:\n{error}"},
    "update_brand_error": {"PL": "Nie udało się zaktualizować marki:\n{error}", "EN": "Failed to update brand:\n{error}"},
    "delete_brand_error": {"PL": "Nie udało się usunąć marki:\n{error}", "EN": "Failed to delete brand:\n{error}"},
    "select_brand_to_edit": {"PL": "Proszę wybrać markę do edycji.", "EN": "Please select a brand to edit."},
    "select_brand_to_delete": {"PL": "Proszę wybrać markę do usunięcia.", "EN": "Please select a brand to delete."},
    "confirm_delete_brand": {"PL": "Czy na pewno chcesz usunąć markę '{name}'?", "EN": "Are you sure you want to delete brand '{name}'?"},
    "edit_brand_title": {"PL": "Edytuj markę", "EN": "Edit Brand"},
    "placeholder_brand": {"PL": "np. eSUN", "EN": "e.g. eSUN"},
    
    # Filament history dialog
    "history_title": {"PL": "Historia - {brand}", "EN": "History - {brand}"},
    "filament_info": {"PL": "Filament:", "EN": "Filament:"},
    "color_info": {"PL": "Kolor:", "EN": "Color:"},
    "initial_weight_info": {"PL": "Waga początkowa (netto):", "EN": "Initial weight (net):"},
    "spool_weight_info_label": {"PL": "Waga szpuli:", "EN": "Spool weight:"},
    "current_weight_info": {"PL": "Waga aktualna (netto):", "EN": "Current weight (net):"},
    
    # Messages
    "confirm_delete": {"PL": "Potwierdzenie usunięcia", "EN": "Confirm Delete"},
    "confirm_delete_filament": {"PL": "Czy na pewno chcesz usunąć filament:", "EN": "Are you sure you want to delete filament:"},
    "confirm_delete_print": {"PL": "Czy na pewno chcesz usunąć ten wydruk z historii?", "EN": "Are you sure you want to delete this print from history?"},
    "weight_will_be_restored": {"PL": "Waga {weight}g zostanie przywrócona do filamentu.", "EN": "Weight of {weight}g will be restored to filament."},
    "print_deleted": {"PL": "Wydruk został usunięty, a waga przywrócona.", "EN": "Print has been deleted and weight restored."},
    "delete_print_btn": {"PL": "🗑️ Usuń wydruk", "EN": "🗑️ Delete Print"},
    "select_print_to_delete": {"PL": "Proszę wybrać wydruk do usunięcia.", "EN": "Please select a print to delete."},
    "irreversible": {"PL": "Ta operacja jest nieodwracalna!", "EN": "This operation is irreversible!"},
    "success": {"PL": "Sukces", "EN": "Success"},
    "error": {"PL": "Błąd", "EN": "Error"},
    "filament_deleted": {"PL": "Filament został usunięty.", "EN": "Filament has been deleted."},
    "delete_failed": {"PL": "Nie udało się usunąć filamentu.", "EN": "Failed to delete filament."},
    "filament_not_found": {"PL": "Filament nie został znaleziony.", "EN": "Filament not found."},
    "no_files": {"PL": "Brak plików", "EN": "No Files"},
    "no_files_to_load": {"PL": "Brak plików do załadowania.", "EN": "No files to load."},
    "no_files_found": {"PL": "Nie znaleziono żadnych plików.", "EN": "No files found."},
    "add_gcode_first": {"PL": "Dodaj pliki G-code przed obliczeniem.", "EN": "Add G-code files before calculating."},
    "select_filament_first": {"PL": "Proszę wybrać filament z magazynu.", "EN": "Please select filament from inventory."},
    "print_recorded": {"PL": "Wydruk zapisany", "EN": "Print Recorded"},
    "print_recorded_msg": {"PL": "Wydruk został zapisany!\n\nFilament: {brand} - {type}\nZużyta waga: {weight} g\nCena: {price}", "EN": "Print has been recorded!\n\nFilament: {brand} - {type}\nWeight used: {weight} g\nPrice: {price}"},
    "print_recorded_multicolor_msg": {"PL": "Wydruk multicolor został zapisany!\n\nNazwa: {name}\nFilamenty: {filaments}\nCałkowita waga: {weight} g\nCałkowita cena: {price}", "EN": "Multicolor print has been recorded!\n\nName: {name}\nFilaments: {filaments}\nTotal weight: {weight} g\nTotal price: {price}"},
    "calculate_first": {"PL": "Najpierw oblicz cenę.", "EN": "Calculate price first."},
    "enter_print_name": {"PL": "Nazwa wydruku", "EN": "Print Name"},
    "enter_print_name_prompt": {"PL": "Podaj nazwę wydruku:", "EN": "Enter print name:"},
    "insufficient_filament": {"PL": "Niewystarczająca ilość filamentu", "EN": "Insufficient filament"},
    "not_enough_filament": {"PL": "Niewystarczająca waga dostępna. Dostępna: {weight} g", "EN": "Insufficient weight available. Available: {weight} g"},
    "validation_error": {"PL": "Błąd walidacji", "EN": "Validation Error"},
    "all_fields_numbers": {"PL": "Wszystkie pola muszą zawierać prawidłowe liczby.", "EN": "All fields must contain valid numbers."},
    "filament_must_be_positive": {"PL": "Zużycie filamentu musi być większe od zera.", "EN": "Filament usage must be greater than zero."},
    "time_must_be_positive": {"PL": "Czas druku musi być większy od zera.", "EN": "Print time must be greater than zero."},
    "material_not_found": {"PL": "Materiał {material} nie został znaleziony w ustawieniach.", "EN": "Material {material} was not found in settings."},
    "brand_not_found": {"PL": "Marka {brand} nie została znaleziona w ustawieniach.", "EN": "Brand {brand} was not found in settings."},
    "brand_not_found_details": {"PL": "Marka '{brand}' dla materiału '{material}' nie została znaleziona w ustawieniach.\n\nDostępne marki: {available}\n\nProszę dodać markę w Ustawieniach > Materiały.", "EN": "Brand '{brand}' for material '{material}' was not found in settings.\n\nAvailable brands: {available}\n\nPlease add the brand in Settings > Materials."},
    "calculation_error": {"PL": "Błąd obliczeń", "EN": "Calculation Error"},
    "calculation_error_msg": {"PL": "Wystąpił błąd podczas obliczeń: {error}", "EN": "An error occurred during calculation: {error}"},
    "print_error": {"PL": "Nie udało się wykonać wydruku: {error}", "EN": "Failed to execute print: {error}"},
    "import_gcode": {"PL": "Import G-code", "EN": "Import G-code"},
    "import_success": {"PL": "Zaimportowano {success} z {total} plików:\n\nSuma czasu: {time} h\nSuma filamentu: {weight} g", "EN": "Imported {success} of {total} files:\n\nTotal time: {time} h\nTotal filament: {weight} g"},
    "import_success_multicolor": {"PL": "Zaimportowano {success} z {total} plików (multicolor - {filaments} filamentów):\n\nSuma czasu: {time} h\nSuma filamentu: {weight} g", "EN": "Imported {success} of {total} files (multicolor - {filaments} filaments):\n\nTotal time: {time} h\nTotal filament: {weight} g"},
    "import_no_data": {"PL": "Nie znaleziono danych w żadnym z {total} wybranych plików.", "EN": "No data found in any of the {total} selected files."},
    "select_gcode_files": {"PL": "Wybierz pliki G-code", "EN": "Select G-code files"},
    "print_name_default": {"PL": "Wydruk", "EN": "Print"},
    
    # Language
    "language": {"PL": "🌐 EN", "EN": "🌐 PL"},
    "language_pl": {"PL": "🌐 Polski", "EN": "🌐 Polish"},
    "language_en": {"PL": "🌐 Angielski", "EN": "🌐 English"},
    "currency_pln": {"PL": "💰 Złoty (PLN)", "EN": "💰 Zloty (PLN)"},
    "currency_eur": {"PL": "💰 Euro (EUR)", "EN": "💰 Euro (EUR)"},
    "currency_usd": {"PL": "💰 Dolar (USD)", "EN": "💰 Dollar (USD)"},
    "currency_gbp": {"PL": "💰 Funt (GBP)", "EN": "💰 Pound (GBP)"},
}


def get_text(key: str) -> str:
    """Get translated text for the current language."""
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(_current_language, TRANSLATIONS[key].get("PL", key))
    return key


def get_language() -> str:
    """Get current language code."""
    return _current_language


def set_language(lang: str):
    """Set current language and notify all registered callbacks."""
    global _current_language
    if lang in ["PL", "EN"]:
        _current_language = lang
        # Save preferences
        save_preferences()
        # Notify all registered callbacks
        for callback in _language_change_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in language change callback: {e}")


def toggle_language():
    """Toggle between PL and EN."""
    global _current_language
    _current_language = "EN" if _current_language == "PL" else "PL"
    # Save preferences
    save_preferences()
    # Notify all registered callbacks
    for callback in _language_change_callbacks:
        try:
            callback()
        except Exception as e:
            print(f"Error in language change callback: {e}")


def register_language_callback(callback: Callable):
    """Register a callback to be called when language changes."""
    if callback not in _language_change_callbacks:
        _language_change_callbacks.append(callback)


def unregister_language_callback(callback: Callable):
    """Unregister a language change callback."""
    if callback in _language_change_callbacks:
        _language_change_callbacks.remove(callback)


# Shortcut function for convenience
def t(key: str) -> str:
    """Shortcut for get_text()."""
    return get_text(key)


# ============== Currency Functions ==============

def get_currency() -> str:
    """Get current currency code."""
    return _current_currency


def set_currency(currency: str):
    """Set current currency and notify all registered callbacks."""
    global _current_currency
    if currency in CURRENCIES:
        _current_currency = currency
        # Save preferences
        save_preferences()
        # Notify all registered callbacks
        for callback in _currency_change_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in currency change callback: {e}")


def get_currency_symbol() -> str:
    """Get current currency symbol."""
    return CURRENCIES[_current_currency]["symbol"]


def get_currency_position() -> str:
    """Get current currency symbol position (before/after)."""
    return CURRENCIES[_current_currency]["position"]


def get_exchange_rate() -> float:
    """Get exchange rate from PLN to current currency."""
    return CURRENCIES[_current_currency]["rate"]


def format_currency(value: float) -> str:
    """Format a value in the current currency."""
    converted = value * get_exchange_rate()
    symbol = get_currency_symbol()
    position = get_currency_position()
    
    if position == "before":
        return f"{symbol}{converted:.2f}"
    else:
        return f"{converted:.2f} {symbol}"


def cycle_currency():
    """Cycle through available currencies."""
    global _current_currency
    currency_list = list(CURRENCIES.keys())
    current_index = currency_list.index(_current_currency)
    next_index = (current_index + 1) % len(currency_list)
    _current_currency = currency_list[next_index]
    
    # Save preferences
    save_preferences()
    
    # Notify all registered callbacks
    for callback in _currency_change_callbacks:
        try:
            callback()
        except Exception as e:
            print(f"Error in currency change callback: {e}")


def register_currency_callback(callback: Callable):
    """Register a callback to be called when currency changes."""
    if callback not in _currency_change_callbacks:
        _currency_change_callbacks.append(callback)


def unregister_currency_callback(callback: Callable):
    """Unregister a currency change callback."""
    if callback in _currency_change_callbacks:
        _currency_change_callbacks.remove(callback)


def get_currency_per_hour() -> str:
    """Get currency suffix for per hour (e.g., 'zł/h', '€/h', '$/h')."""
    symbol = get_currency_symbol()
    return f"{symbol}/h"


def get_currency_per_kg() -> str:
    """Get currency suffix for per kg (e.g., 'zł/kg', '€/kg', '$/kg')."""
    symbol = get_currency_symbol()
    return f"{symbol}/kg"


def get_currency_per_kwh() -> str:
    """Get currency suffix for per kWh (e.g., 'zł/kWh', '€/kWh', '$/kWh')."""
    symbol = get_currency_symbol()
    return f"{symbol}/kWh"


def convert_from_pln(value_pln: float) -> float:
    """
    Convert value from PLN to current currency.
    
    Args:
        value_pln: Value in PLN
        
    Returns:
        Value converted to current currency
    """
    return value_pln * get_exchange_rate()


def convert_to_pln(value_current: float) -> float:
    """
    Convert value from current currency to PLN.
    
    Args:
        value_current: Value in current currency
        
    Returns:
        Value converted to PLN
    """
    return value_current / get_exchange_rate()


def load_preferences():
    """Load user preferences (language and currency) from file."""
    global _current_language, _current_currency
    
    # Try to load from preferences file first
    if os.path.exists(PREFERENCES_FILE):
        try:
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                if "language" in prefs and prefs["language"] in ["PL", "EN"]:
                    _current_language = prefs["language"]
                if "currency" in prefs and prefs["currency"] in CURRENCIES:
                    _current_currency = prefs["currency"]
                return
        except Exception as e:
            print(f"Error loading preferences: {e}")
    
    # Fallback: try to load from calculator config
    try:
        from utils.price_calculator import ConfigManager
        config = ConfigManager.load_config()
        if "preferences" in config:
            prefs = config["preferences"]
            if "language" in prefs and prefs["language"] in ["PL", "EN"]:
                _current_language = prefs["language"]
            if "currency" in prefs and prefs["currency"] in CURRENCIES:
                _current_currency = prefs["currency"]
    except Exception as e:
        print(f"Error loading preferences from config: {e}")


def save_preferences():
    """Save user preferences (language and currency) to file."""
    global _current_language, _current_currency
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PREFERENCES_FILE), exist_ok=True)
        
        # Save to preferences file
        prefs = {
            "language": _current_language,
            "currency": _current_currency
        }
        
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
        
        # Also save to calculator config for backward compatibility
        try:
            from utils.price_calculator import ConfigManager
            config = ConfigManager.load_config()
            if "preferences" not in config:
                config["preferences"] = {}
            config["preferences"]["language"] = _current_language
            config["preferences"]["currency"] = _current_currency
            ConfigManager.save_config(config)
        except Exception as e:
            print(f"Error saving preferences to config: {e}")
            
    except Exception as e:
        print(f"Error saving preferences: {e}")
