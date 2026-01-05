# 3D Print Manager

Aplikacja do zarządzania filamentami i kalkulacji cen wydruków 3D. Umożliwia śledzenie zapasów filamentów, obliczanie kosztów wydruków oraz zarządzanie historią projektów.

## Funkcje

- **Kalkulator cen wydruków** - Automatyczne obliczanie kosztów na podstawie plików G-code
- **Zarządzanie magazynem filamentów** - Śledzenie zapasów, wag i historii użycia
- **Historia wydruków** - Pełna historia projektów z możliwością edycji
- **Wielojęzyczność** - Obsługa języka polskiego i angielskiego
- **Wielowalutowość** - Obsługa PLN, EUR, USD, GBP z automatyczną konwersją
- **Zarządzanie markami** - Dodawanie, edycja i usuwanie marek filamentów
- **Zaawansowane ustawienia** - Konfiguracja stawek, marż, VAT i innych parametrów

## Wymagania systemowe

- Python 3.8 lub nowszy
- PyQt5 5.15.0 lub nowszy
- Windows, Linux lub macOS

## Instalacja

### 1. Sklonuj repozytorium

```bash
git clone https://github.com/twoj-username/print-manager.git
cd print-manager
```

### 2. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 3. Uruchom aplikację

```bash
python app.py
```

## Pierwsze uruchomienie

Przy pierwszym uruchomieniu aplikacja automatycznie utworzy:
- Folder `data/` z plikami konfiguracyjnymi
- Domyślne ustawienia kalkulatora
- Puste bazy danych dla filamentów, marek i wydruków

## Struktura projektu

```
PrintManager/
├── app.py                 # Główny plik aplikacji
├── dialogs/               # Dialogi (ustawienia, edycja, itp.)
│   ├── add_filament_dialog.py
│   ├── brands_dialog.py
│   ├── edit_filament_dialog.py
│   ├── edit_print_dialog.py
│   ├── settings_dialog.py
│   └── ...
├── tabs/                  # Zakładki głównego okna
│   ├── calculator_tab.py
│   ├── history_tab.py
│   └── inventory_tab.py
├── utils/                 # Narzędzia pomocnicze
│   ├── db_handler.py     # Zarządzanie danymi JSON
│   ├── gcode_parser.py    # Parsowanie plików G-code
│   ├── price_calculator.py # Kalkulacja cen
│   └── translations.py    # System tłumaczeń
├── data/                  # Dane użytkownika (tworzone automatycznie)
│   ├── brands.json
│   ├── filaments.json
│   ├── prints.json
│   ├── calculator_config.json
│   └── preferences.json
└── requirements.txt       # Zależności Python
```

## Użycie

### Dodawanie filamentu

1. Przejdź do zakładki **Magazyn**
2. Kliknij **Dodaj filament**
3. Wypełnij formularz (marka, typ, kolor, waga)
4. Zapisz

### Obliczanie ceny wydruku

1. Przejdź do zakładki **Kalkulator**
2. Dodaj pliki G-code (przeciągnij i upuść lub użyj przycisku)
3. Wybierz filament z magazynu
4. Kliknij **Oblicz cenę**
5. Zapisz wydruk do historii (opcjonalnie)

### Zarządzanie markami

1. W zakładce **Magazyn** kliknij **Marki**
2. Dodaj nową markę lub edytuj/usuń istniejącą
3. Ustaw wagę szpuli dla każdej marki

### Ustawienia

1. Kliknij przycisk **Ustawienia** w górnym pasku
2. Skonfiguruj:
   - Stawki godzinowe dla materiałów
   - Ceny filamentów per kg
   - Koszty energii
   - Marże i VAT
   - Zaawansowane opcje

## Konfiguracja

Wszystkie ustawienia są przechowywane w pliku `data/calculator_config.json`. Możesz edytować go ręcznie lub użyć interfejsu aplikacji.

## Języki i waluty

Aplikacja obsługuje:
- **Języki**: Polski (PL), Angielski (EN)
- **Waluty**: PLN, EUR, USD, GBP

Preferencje są zapisywane automatycznie i przywracane przy następnym uruchomieniu.

## Rozwiązywanie problemów

### Aplikacja nie uruchamia się

- Sprawdź czy masz zainstalowany Python 3.8+
- Sprawdź czy wszystkie zależności są zainstalowane: `pip install -r requirements.txt`

### Błędy związane z danymi

- Jeśli pliki w folderze `data/` są uszkodzone, usuń je - aplikacja utworzy nowe z domyślnymi wartościami

## Autor

Konrad Małecki

## Wsparcie

W razie problemów lub pytań, utwórz issue w repozytorium GitHub.

