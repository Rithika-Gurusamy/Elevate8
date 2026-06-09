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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ProjectMigrationSuggestion:
    suggestions: Dict[str, FileMigrationSuggestion] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {path: sug.to_dict() for path, sug in self.suggestions.items()}
