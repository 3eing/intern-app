from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @property
    def uploads(self) -> Path:
        return self.root / "uploads"

    @property
    def generated(self) -> Path:
        return self.root / "generated"

    @property
    def eep_uploads(self) -> Path:
        return self.uploads / "eepower"

    @property
    def linepole_uploads(self) -> Path:
        return self.uploads / "linepole_generator"

    @property
    def dev_uploads(self) -> Path:
        return self.uploads / "developpement"

    @property
    def dev_template_tmp(self) -> Path:
        return self.dev_uploads / "templates"

    @property
    def dev_generated(self) -> Path:
        return self.generated / "developpement"

    @property
    def dev_docs_output(self) -> Path:
        return self.dev_generated / "doc"