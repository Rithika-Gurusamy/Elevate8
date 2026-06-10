from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

@dataclass
class RiskFinding:
    indicator: str
    impact: str
    count: int
    files: List[str]
    remediation: str

@dataclass
class MigrationRiskReport:
    risk_score: int
    risk_category: str
    findings: List[RiskFinding] = field(default_factory=list)
    legacy_packages: List[str] = field(default_factory=list)
    unsupported_apis: List[str] = field(default_factory=list)
    config_complexity_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to a JSON serializable dict."""
        return asdict(self)
