from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

@dataclass
class FileMigrationSuggestion:
    file_path: str
    summary: str
    migration_strategy: str
    unsupported_apis: List[str] = field(default_factory=list)
    dotnet8_equivalent: str = ""
    code_diff_markdown: str = ""
    confidence_score: float = 0.0

    def __post_init__(self):
        # Normalize migration_strategy to string
        if isinstance(self.migration_strategy, list):
            self.migration_strategy = "\n".join(str(s) for s in self.migration_strategy)
        elif self.migration_strategy is not None:
            self.migration_strategy = str(self.migration_strategy)
        else:
            self.migration_strategy = ""

        # Normalize summary to string
        if isinstance(self.summary, list):
            self.summary = "\n".join(str(s) for s in self.summary)
        elif self.summary is not None:
            self.summary = str(self.summary)
        else:
            self.summary = ""

        # Normalize unsupported_apis to list of strings
        if isinstance(self.unsupported_apis, str):
            self.unsupported_apis = [self.unsupported_apis]
        elif isinstance(self.unsupported_apis, list):
            self.unsupported_apis = [str(x) for x in self.unsupported_apis]
        else:
            self.unsupported_apis = []

        # Normalize confidence_score to float
        try:
            self.confidence_score = float(self.confidence_score)
        except (ValueError, TypeError):
            self.confidence_score = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ProjectMigrationSuggestion:
    suggestions: Dict[str, FileMigrationSuggestion] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {path: sug.to_dict() for path, sug in self.suggestions.items()}
