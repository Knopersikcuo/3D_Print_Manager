"""
G-code parser for extracting print time, filament weight, and material type.
Supports both text .gcode and binary .bgcode (PrusaSlicer/Bambu Studio) formats.
"""

import os
import re
from typing import Dict


class GCodeParser:
    """Parser for G-code files to extract print time and filament usage."""

    @staticmethod
    def _parse_filename_time(filename: str) -> float:
        """Parse time from filename (e.g., 'file_2h36m.bgcode' -> 2.6 hours)."""
        # Pattern: XhYm or XhYmZs
        time_pattern = r'(\d+)h\s*(\d+)m(?:\s*(\d+)s)?'
        match = re.search(time_pattern, filename, re.IGNORECASE)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3) or 0)
            return hours + minutes / 60.0 + seconds / 3600.0
        return 0.0

    @staticmethod
    def _parse_filename_material(filename: str) -> str:
        """
        Parse material type from filename (e.g., 'file_PETG_2h36m.gcode' -> 'PETG').
        
        Args:
            filename (str): Filename to parse.
            
        Returns:
            str: Material type if found, empty string otherwise.
        """
        # Common material names to search for in filename
        materials = ['PETG', 'PLA', 'ABS', 'ASA', 'PP', 'TPU', 'NYLON', 'PA', 'PC', 'POLYCARBONATE', 'PET']
        
        filename_upper = filename.upper()
        for material in materials:
            # Look for material name in filename (case-insensitive)
            if material in filename_upper:
                # Normalize PET to PETG
                if material == 'PET':
                    return 'PETG'
                return material
        
        return ""

    @staticmethod
    def parse_gcode(file_path: str) -> Dict:
        """
        Parse G-code file to extract print time, filament weight, and material type.
        Supports both text .gcode and binary .bgcode (PrusaSlicer/Bambu Studio) formats.
        
        For .bgcode files (binary format):
        - Time is extracted from 'estimated printing time (normal mode)=' field in file content (primary)
        - Time fallback: extracted from filename if not found in content (e.g., 'file_2h36m.bgcode' -> 2.6 hours)
        - Filament weight is extracted from 'filament used [g]=' field in file content
        - Material type is extracted from 'filament_type=' field in file content
        
        For .gcode files (text format):
        - Time is extracted from 'estimated printing time (normal mode)=' or similar patterns in file content
        - Time fallback: extracted from filename if not found in content
        - Filament weight is extracted from 'filament used [g]=' field in file content
        - Material type is extracted from 'filament_type=' field in file content

        Args:
            file_path (str): Path to G-code file (.gcode or .bgcode).

        Returns:
            Dict: Dictionary with 'time_hours', 'filament_weight_g', and 'material_type' keys.
        """
        result = {"time_hours": 0.0, "filament_weight_g": 0.0, "material_type": ""}
        filename = os.path.basename(file_path)

        try:
            # Check if file is .bgcode (binary format - PrusaSlicer/Bambu Studio)
            if file_path.lower().endswith('.bgcode'):
                # Try to read as binary and search for text metadata
                with open(file_path, 'rb') as f:
                    # Read larger chunk (128KB) to catch metadata that might be deeper
                    data = f.read(131072)
                    # Try to decode as UTF-8 (may contain readable metadata)
                    try:
                        content = data.decode('utf-8', errors='ignore')
                    except:
                        content = ""

                # Search for print time in file content first (primary method)
                time_patterns = [
                    r'estimated printing time \(normal mode\)\s*=\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',  # PrusaSlicer: estimated printing time (normal mode)=2h 35m 36s
                    r'estimated printing time\s*=\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',  # Alternative: estimated printing time=2h 35m 36s
                    r'print_time\s*[:=]\s*(\d+)',  # Alternative: print_time: 1234 (seconds)
                    r'time\s*[:=]\s*(\d+)',  # Alternative: time: 1234
                ]

                for pattern in time_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        if len(match.groups()) == 1:
                            # Seconds only
                            seconds = int(match.group(1))
                            if seconds > 10000:  # Likely milliseconds
                                result["time_hours"] = seconds / 3600000.0
                            else:
                                result["time_hours"] = seconds / 3600.0
                        else:
                            # Hours, minutes, seconds
                            hours = int(match.group(1) or 0)
                            minutes = int(match.group(2) or 0)
                            seconds = int(match.group(3) or 0)
                            result["time_hours"] = hours + minutes / 60.0 + seconds / 3600.0
                        break

                # Fallback: parse time from filename if not found in content
                if result["time_hours"] == 0.0:
                    result["time_hours"] = GCodeParser._parse_filename_time(filename)

                # Search for PrusaSlicer format: 'filament used [g]=35.79' or multicolor: 'total filament weight [g] : 30.98,1.12'
                filament_patterns = [
                    r'total filament weight\s*\[g\]\s*[:=]\s*([\d.,\s]+)',  # Multicolor: total filament weight [g] : 30.98,1.12
                    r'filament used \[g\]\s*=\s*([\d.]+)',  # PrusaSlicer: filament used [g]=35.79
                    r'filament_weight["\']?\s*[:=]\s*([\d.]+)',  # Alternative: filament_weight: 12.34
                    r'weight["\']?\s*[:=]\s*([\d.]+)',  # Alternative: weight: 12.34
                    r'([\d.]+)\s*g(?:ram)?',  # Generic: 12.34g
                ]

                for pattern in filament_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        value_str = match.group(1).strip()
                        
                        # Check if it's multicolor (contains comma)
                        if ',' in value_str:
                            # Parse multiple weights: "30.98,1.12" -> [30.98, 1.12]
                            weights = [float(w.strip()) for w in value_str.split(',') if w.strip()]
                            if weights:
                                result["filament_weights_g"] = weights
                                result["filament_weight_g"] = sum(weights)  # Total for backward compatibility
                        else:
                            result["filament_weight_g"] = float(value_str)
                        break

                # Search for material type: 'filament_type=PETG'
                material_patterns = [
                    r'filament_type\s*=\s*(\w+)',  # PrusaSlicer: filament_type=PETG
                    r'filament["\']?\s*[:=]\s*["\']?(\w+)["\']?',  # Alternative formats
                    r'material["\']?\s*[:=]\s*["\']?(\w+)["\']?',
                ]

                for pattern in material_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        material = match.group(1).upper().strip()
                        # Normalize common material names
                        material_mapping = {
                            'PLA': 'PLA',
                            'PETG': 'PETG',
                            'ABS': 'ABS',
                            'ASA': 'ASA',
                            'PP': 'PP',
                            'TPU': 'TPU',
                            'NYLON': 'NYLON',
                            'PA': 'PA',
                            'PC': 'PC',
                            'POLYCARBONATE': 'PC',
                            'PET': 'PETG',  # Sometimes PET is used for PETG
                        }
                        result["material_type"] = material_mapping.get(material, material)
                        break
                
                # Fallback: try to extract material from filename if not found in file
                if not result["material_type"]:
                    result["material_type"] = GCodeParser._parse_filename_material(filename)

            else:
                # Standard text G-code file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Extract print time (common formats: ;TIME:1234 or ; estimated printing time = 1h 2m 3s)
                time_patterns = [
                    r';TIME:(\d+)',  # Cura format: ;TIME:1234 (seconds)
                    r'; estimated printing time \(normal mode\)\s*=\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',  # PrusaSlicer format with (normal mode)
                    r'; estimated printing time \(silent mode\)\s*=\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',  # PrusaSlicer format with (silent mode)
                    r'; estimated printing time\s*=\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',  # PrusaSlicer format without mode
                    r';Print time: (?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',  # Alternative format
                    r';TIME_ELAPSED:([\d.]+)',  # Alternative time format
                ]

                for pattern in time_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        if len(match.groups()) == 1:  # Seconds only
                            seconds = float(match.group(1))
                            result["time_hours"] = seconds / 3600.0
                        else:  # Hours, minutes, seconds
                            hours = int(match.group(1) or 0)
                            minutes = int(match.group(2) or 0)
                            seconds = int(match.group(3) or 0)
                            result["time_hours"] = hours + minutes / 60.0 + seconds / 3600.0
                        break

                # Fallback: parse time from filename if not found in content
                if result["time_hours"] == 0.0:
                    result["time_hours"] = GCodeParser._parse_filename_time(filename)

                # Extract filament weight (common formats: ;Filament used: 12.34m or ;Weight: 12.34g)
                # Support multicolor: ; total filament weight [g] : 30.98,1.12
                filament_patterns = [
                    r';\s*total filament weight\s*\[g\]\s*[:=]\s*([\d.,\s]+)',  # Multicolor: ; total filament weight [g] : 30.98,1.12
                    r';\s*filament used \[g\]\s*=\s*([\d.]+)',  # PrusaSlicer format: ; filament used [g] = 32.93 (priority - most common)
                    r';\s*total filament used \[g\]\s*=\s*([\d.]+)',  # PrusaSlicer format: ; total filament used [g] = 32.93
                    r';Filament used:\s*([\d.]+)\s*m',  # Meters
                    r';Weight:\s*([\d.]+)\s*g',  # Grams
                    r';Filament weight:\s*([\d.]+)\s*g',  # Alternative
                    r';Filament length:\s*([\d.]+)\s*m',  # Filament length in meters
                ]

                for pattern in filament_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        value_str = match.group(1).strip()
                        
                        # Check if it's multicolor (contains comma)
                        if ',' in value_str:
                            # Parse multiple weights: "30.98,1.12" -> [30.98, 1.12]
                            weights = [float(w.strip()) for w in value_str.split(',') if w.strip()]
                            if weights:
                                result["filament_weights_g"] = weights
                                result["filament_weight_g"] = sum(weights)  # Total for backward compatibility
                        else:
                            # Single weight
                            value = float(value_str)
                            # Check if pattern is for grams (has [g] or ends with \s*g)
                            if r'\[g\]' in pattern or r'\s*g' in pattern:
                                # Value is already in grams, use as-is
                                result["filament_weight_g"] = value
                            elif r'\s*m' in pattern or (r'\[m\]' in pattern):
                                # Value is in meters, convert to grams (assuming 1.75mm filament)
                                # Approximate: 1m of 1.75mm filament ≈ 2.7g (depends on material density)
                                result["filament_weight_g"] = value * 2.7
                            else:
                                # Default: assume grams
                                result["filament_weight_g"] = value
                        break

                # Search for material type in text G-code
                material_patterns = [
                    r';\s*filament_type\s*[:=]\s*(\w+)',  # ; filament_type = PETG or ;filament_type: PETG
                    r';\s*material\s*[:=]\s*(\w+)',  # ; material: PETG
                    r'filament_type\s*=\s*(\w+)',  # filament_type=PETG (without semicolon)
                ]

                for pattern in material_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        material = match.group(1).upper().strip()
                        material_mapping = {
                            'PLA': 'PLA',
                            'PETG': 'PETG',
                            'ABS': 'ABS',
                            'ASA': 'ASA',
                            'PP': 'PP',
                            'TPU': 'TPU',
                            'NYLON': 'NYLON',
                            'PA': 'PA',
                            'PC': 'PC',
                            'POLYCARBONATE': 'PC',
                            'PET': 'PETG',  # Sometimes PET is used for PETG
                        }
                        result["material_type"] = material_mapping.get(material, material)
                        break
                
                # Fallback: try to extract material from filename if not found in file
                if not result["material_type"]:
                    result["material_type"] = GCodeParser._parse_filename_material(filename)

        except Exception as e:
            print(f"Error parsing G-code: {e}")
            # Try filename parsing as last resort
            if result["time_hours"] == 0.0:
                result["time_hours"] = GCodeParser._parse_filename_time(filename)

        return result

