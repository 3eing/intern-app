import re
from pathlib import Path

import pandas as pd


SCENARIO_PATTERN = r"(?i)(lv|lm|hv|30_cycle_report).+(scen\D*)(\s*_*-*)(\d+\w{0,1})"


def scenario_number(file: Path) -> str | None:
    match = re.search(SCENARIO_PATTERN, file.name)
    return match.groups()[-1] if match else None


def group_by_scenario(files: list[Path], scenario: str) -> list[Path]:
    return [file for file in files if scenario_number(file) == scenario]


def scenario_finder(files: list[Path]) -> list[str]:
    scenarios: list[str] = []
    for file in files:
        scenario = scenario_number(file)
        if scenario and scenario not in scenarios:
            scenarios.append(scenario)
    return scenarios


def pire_cas(reports: list[pd.DataFrame], scenarios: list[str]) -> pd.DataFrame:
    worst_case = pd.concat(reports, keys=scenarios, names=["Scénario", None])
    worst_case = worst_case.loc[worst_case.groupby(level=1)["Asym Amps"].idxmax()]
    worst_case = worst_case.sort_values(by="Bus (V)", ascending=False)
    return worst_case.reset_index("Scénario")
