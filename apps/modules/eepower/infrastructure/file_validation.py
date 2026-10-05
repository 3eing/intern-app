import re
from pathlib import Path
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

import openpyxl
import pandas as pd

from modules.eepower.domain.services import scenario_number
from modules.eepower.infrastructure.parsers import parse_excel_sheet
from modules.shared.infrastructure.error_handlers import FileError


REPORT_PATTERNS = {
    "CC": r"(?i)(.*LM|.*LV.Momentary)|(.*30.Cycle)",
    "AF": r"(?i)Arc.Flash",
    "ED": r"(?i)Equipment.Duty",
    "TCC": r"(?i)TCC.coordination",
}

REPORT_FORMATS = {
    "CC": ("Courts-circuits (CC)", (".csv", ".xlsx")),
    "AF": ("Arc Flash (AF)", (".xlsx",)),
    "ED": ("Equipment Duty (ED)", (".xlsx",)),
    "TCC": ("TCC Coordination (TCC)", (".xlsx",)),
}


def validate_report_filename(file: str | Path) -> str:
    file = Path(file)
    if file.suffix.lower() not in {".csv", ".xlsx"}:
        raise FileError(f"'{file.name}' : extension non prise en charge. Formats possibles : .csv ou .xlsx selon le rapport ; .xls est refusé.")
    for report_type, pattern in REPORT_PATTERNS.items():
        if re.match(pattern, file.name):
            label, extensions = REPORT_FORMATS[report_type]
            if file.suffix.lower() not in extensions:
                raise FileError(f"'{file.name}' : le rapport {label} doit être exporté au format {' ou '.join(extensions)}. Réexportez-le depuis EasyPower ; changer son extension ne suffit pas.")
            if report_type == "CC" and scenario_number(file) is None:
                raise FileError(f"'{file.name}' : ajoutez un numéro de scénario à la fin du nom, avant l'extension, par exemple 'LV_Momentary_scen_1.csv' ou '30_Cycle_Report_scen_1.xlsx'. Utilisez le même scénario pour les rapports associés.")
            return report_type
    raise FileError(f"Le fichier '{file.name}' n'est pas reconnu. Conservez le nom du rapport exporté par EasyPower.")

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
    report_type = validate_report_filename(file_path)
    try:
        if file_path.stat().st_size == 0:
            raise FileError(f"Le fichier '{file_path.name}' est vide.")
        if report_type == "CC":
            if file_path.suffix.lower() == ".csv":
                dataframe = pd.read_csv(file_path, skiprows=1)
            else:
                dataframe = pd.read_excel(file_path, skiprows=7, engine="openpyxl")
            return _validate_columns(file_path, dataframe, CC_COLUMNS, "CC")

        if report_type == "AF":
            return _validate_columns(file_path, pd.read_excel(file_path, engine="openpyxl"), AF_COLUMNS, "AF")

        if report_type == "ED":
            return _validate_columns(file_path, pd.read_excel(file_path, engine="openpyxl"), ED_COLUMNS, "ED")

        if report_type == "TCC":
            tables = parse_excel_sheet(file_path, header=[0, 1])
            if not tables:
                raise FileError(f"Aucun tableau de protection trouvé dans '{file_path.name}'.")
            first_level = set(tables[0].columns.get_level_values(0))
            if not TCC_COLUMNS.intersection(first_level):
                raise FileError(f"Colonnes de protection manquantes dans '{file_path.name}'")
            return "TCC"
    except (BadZipFile, openpyxl.utils.exceptions.InvalidFileException, ParseError, KeyError) as error:
        raise FileError(f"'{file_path.name}' n'est pas un classeur XLSX valide ou sa structure est endommagée. Réexportez le rapport depuis EasyPower ; changer son extension ne suffit pas.") from error
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise FileError(f"Impossible de lire le CSV '{file_path.name}'. Vérifiez son encodage UTF-8, son séparateur virgule et son contenu.") from error
    except ValueError as error:
        raise FileError(f"Le contenu du fichier '{file_path.name}' est invalide : {error}") from error

    raise FileError(f"Le fichier '{file_path.name}' n'est pas géré par cet outil")
