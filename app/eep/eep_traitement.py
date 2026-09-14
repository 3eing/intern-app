"""Deprecated compatibility exports for the former EasyPower processing module."""

from modules.eepower.application.process_reports import generate_reports
from modules.eepower.infrastructure.report_builder import (
    df_to_tabularay,
    report_af,
    report_cc,
    report_ed,
    report_tcc,
)

__all__ = [
    "df_to_tabularay",
    "generate_reports",
    "report_af",
    "report_cc",
    "report_ed",
    "report_tcc",
]
