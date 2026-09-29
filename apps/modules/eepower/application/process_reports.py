from collections.abc import Mapping
from pathlib import Path
from typing import Any

from modules.eepower.domain.models import EepReportData
from modules.eepower.infrastructure.report_builder import report_af, report_cc, report_ed, report_tcc


REPORT_BUILDERS = {
    "CC": report_cc,
    "AF": report_af,
    "ED": report_ed,
    "TCC": report_tcc,
}


def generate_reports(data: Mapping[str, Any], output_dir: Path) -> list[Path]:
    """Generate every report selected by the user and return its output files."""
    report_data = EepReportData.from_mapping(data)
    legacy_data = report_data.as_mapping()
    output_files: list[Path] = []

    for report_type in report_data.report_types:
        report_builder = REPORT_BUILDERS.get(report_type)
        if report_builder is not None:
            output_files.extend(report_builder(legacy_data, output_dir))

    return output_files
