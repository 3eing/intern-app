from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class EepReportData:
    """Input required to generate EasyPower reports."""

    files: list[Path]
    scenarios: list[str]
    bus_exclusions: list[str]
    report_types: list[str]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "EepReportData":
        return cls(
            files=[Path(file) for file in data.get("FILES", [])],
            scenarios=list(data.get("SCENARIOS", [])),
            bus_exclusions=list(data.get("BUS_EXCLUS", [])),
            report_types=list(data.get("REPORT_TYPE", [])),
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "FILES": self.files,
            "SCENARIOS": self.scenarios,
            "NB_SCEN": len(self.scenarios),
            "BUS_EXCLUS": self.bus_exclusions,
            "REPORT_TYPE": self.report_types,
        }
