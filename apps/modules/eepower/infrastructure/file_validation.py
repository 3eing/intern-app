import re
from pathlib import Path

import openpyxl
import pandas as pd

from modules.eepower.infrastructure.parsers import parse_excel_sheet
from modules.shared.infrastructure.error_handlers import FileError


REPORT_PATTERNS = {
    "CC": r"(?i)(.*LM|.*LV.Momentary)|(.*30.Cycle)",
    "AF": r"(?i)Arc.Flash",
    "ED": r"(?i)Equipment.Duty",
    "TCC": r"(?i)TCC.coordination",
}

CC_COLUMNS = {
    "Bus kV",
    "Sym Amps",
}
AF_COLUMNS = {
    "Arc Fault Bus Name", "Worst Case Scenario", "Arc Fault Bus kV", "Fault Type",
    "Upstream Trip Device Name", "Bus Bolted Fault (kA)", "Bus Arc Fault (kA)",
    "Trip Time (sec)", "Arc Time (sec)", "Limited Approach Boundary (m)",
    "Restricted Approach Boundary (m)", "Working Distance (m)",
    "Incident Energy\n(cal/cm2)",
}
ED_COLUMNS = {
    "Equipment\nName", "Worst Case Scenario", "Fault\nType", "Bus Base\nkV",
    "Manufacturer", "Style", "Test\nStandard", "1/2 Cycle\nRating\n(kA)",
    "1/2 Cycle\nDuty\n(kA)", "1/2 Cycle\nDuty\n(%)", "Comments",
}
TCC_COLUMNS = {"Fuse", "SST", "Thermal Magnetic Breaker"}


def _missing_columns(columns: set[str], expected: set[str]) -> set[str]:
    return expected - columns


def _validate_columns(file: Path, dataframe: pd.DataFrame, expected: set[str], report_type: str) -> str:
    missing = _missing_columns(set(dataframe.columns), expected)
    if missing:
        raise FileError(f"Colonnes manquantes dans '{file.name}' : {', '.join(sorted(missing))}")
    return report_type


def validate_file_epow(file: str | Path) -> str:
    """Validate an EasyPower export and return its report type."""
    file_path = Path(file)
    try:
        if re.match(REPORT_PATTERNS["CC"], file_path.name):
            try:
                dataframe = pd.read_csv(file_path, skiprows=1)
            except UnicodeDecodeError:
                dataframe = pd.read_excel(file_path, skiprows=7, engine="openpyxl")
            return _validate_columns(file_path, dataframe, CC_COLUMNS, "CC")

        if re.match(REPORT_PATTERNS["AF"], file_path.name):
            return _validate_columns(file_path, pd.read_excel(file_path, engine="openpyxl"), AF_COLUMNS, "AF")

        if re.match(REPORT_PATTERNS["ED"], file_path.name):
            return _validate_columns(file_path, pd.read_excel(file_path, engine="openpyxl"), ED_COLUMNS, "ED")

        if re.match(REPORT_PATTERNS["TCC"], file_path.name):
            tables = parse_excel_sheet(file_path, header=[0, 1])
            first_level = set(tables[0].columns.get_level_values(0))
            if not TCC_COLUMNS.intersection(first_level):
                raise FileError(f"Colonnes de protection manquantes dans '{file_path.name}'")
            return "TCC"
    except (OSError, ValueError, openpyxl.utils.exceptions.InvalidFileException) as error:
        raise FileError(f"Le fichier '{file_path.name}' est invalide") from error

    raise FileError(f"Le fichier '{file_path.name}' n'est pas géré par cet outil")
