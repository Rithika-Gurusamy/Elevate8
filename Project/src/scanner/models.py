from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class AnalyzedFile:
    file_path: str
    extension: str
    namespaces: List[str] = field(default_factory=list)
    usings: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)  # package -> version extracted if any
    detected_patterns: List[str] = field(default_factory=list)  # indicators detected in this file
    lines_of_code: int = 0

@dataclass
class ProjectAnalysis:
    files: List[AnalyzedFile] = field(default_factory=list)
    technologies: Set[str] = field(default_factory=set)
    dependencies: Dict[str, str] = field(default_factory=dict)  # aggregated package -> version
    detected_patterns: Dict[str, List[str]] = field(default_factory=dict)  # pattern -> list of file paths
    complexity_score: int = 0
