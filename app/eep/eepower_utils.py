"""Deprecated compatibility exports for the former EasyPower utility module."""

from modules.eepower.domain.services import (
    SCENARIO_PATTERN,
    group_by_scenario,
    pire_cas,
    scenario_finder,
    scenario_number,
)
from modules.eepower.infrastructure.parsers import (
    parse_excel_sheet,
    simple_af_report,
    simple_cc_report,
    simple_ed_report,
    simple_tcc_reports,
)

SCEN_PATERN = SCENARIO_PATTERN
scen_num_finder = scenario_number

__all__ = [
    "SCEN_PATERN",
    "group_by_scenario",
    "parse_excel_sheet",
    "pire_cas",
    "scen_num_finder",
    "scenario_finder",
    "simple_af_report",
    "simple_cc_report",
    "simple_ed_report",
    "simple_tcc_reports",
]
