import json
from src.scanner.models import ProjectAnalysis, AnalyzedFile
from src.risk_engine.engine import RiskEngine
from src.risk_engine.models import MigrationRiskReport

def test_low_risk_project():
    # A modern SDK project with no legacy indicators
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(file_path="App.csproj", extension=".csproj", dependencies={"TargetFramework": "net8.0", "Newtonsoft.Json": "13.0.3"}),
            AnalyzedFile(file_path="Program.cs", extension=".cs", lines_of_code=100)
        ],
        technologies={".NET 8.0"},
        dependencies={"TargetFramework": "net8.0", "Newtonsoft.Json": "13.0.3"}
    )
    
    engine = RiskEngine()
    report = engine.evaluate_project(analysis)
    
    assert report.risk_score == 0
    assert report.risk_category == "Low"
    assert len(report.findings) == 0

def test_high_risk_project():
    # A legacy project loaded with WCF, WebForms, System.Web and old packages
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(
                file_path="Legacy.csproj",
                extension=".csproj",
                dependencies={"TargetFrameworkVersion": "v4.7.2", "EntityFramework": "5.0.0", "System.Web.Mvc": "4.0.0.0"}
            ),
            # WCF Service
            AnalyzedFile(
                file_path="Service.svc",
                extension=".svc",
                detected_patterns=["WCF SVC Service File"]
            ),
            AnalyzedFile(
                file_path="Service.svc.cs",
                extension=".cs",
                detected_patterns=["WCF Service Contract"]
            ),
            # WebForms Page
            AnalyzedFile(
                file_path="Default.aspx",
                extension=".aspx",
                detected_patterns=["WebForms ASPX File"]
            ),
            AnalyzedFile(
                file_path="Default.aspx.cs",
                extension=".cs",
                detected_patterns=["WebForms Page", "System.Web Reference", "HttpContext.Current Usage"]
            ),
            # Config file
            AnalyzedFile(
                file_path="web.config",
                extension=".config",
                detected_patterns=["Legacy <system.web> Configuration", "WCF <system.serviceModel> Configuration"]
            )
        ],
        technologies={"WCF", "WebForms", "ASP.NET Legacy", ".NET Framework (Legacy)"},
        dependencies={
            "TargetFrameworkVersion": "v4.7.2",
            "EntityFramework": "5.0.0",
            "System.Web.Mvc": "4.0.0.0"
        },
        detected_patterns={
            "WCF SVC Service File": ["Service.svc"],
            "WCF Service Contract": ["Service.svc.cs"],
            "WebForms ASPX File": ["Default.aspx"],
            "WebForms Page": ["Default.aspx.cs"],
            "System.Web Reference": ["Default.aspx.cs"],
            "HttpContext.Current Usage": ["Default.aspx.cs"],
            "Legacy <system.web> Configuration": ["web.config"],
            "WCF <system.serviceModel> Configuration": ["web.config"]
        }
    )

    engine = RiskEngine()
    report = engine.evaluate_project(analysis)

    # Let's check scoring components:
    # 1. WCF: svc file (2) + contract (1) + web.config (1) = 4 indicators. Ratio: 4/5 = 0.8. Score: 0.8 * 30 = 24.0
    # 2. WebForms: aspx file (2) + Page pattern (1) = 3 indicators. Ratio: 3/10 = 0.3. Score: 0.3 * 30 = 9.0
    # 3. System.Web: System.Web pattern (1) + HttpContext (1) = 2. Ratio: 2/10 = 0.2. Score: 0.2 * 20 = 4.0
    # 4. Legacy Packages: EntityFramework and System.Web.Mvc = 2 packages. Ratio: 2/4 = 0.5. Score: 0.5 * 10 = 5.0
    # 5. Config Complexity: 1 config file (2 pts) + web config legacy (3 pts) + wcf config legacy (5 pts) = 10 pts. Ratio: 1.0. Score: 10.0
    # Total expected score = 24 + 9 + 4 + 5 + 10 = 52
    assert report.risk_score == 52
    assert report.risk_category == "Medium"
    
    # Verify findings are populated
    indicators = [f.indicator for f in report.findings]
    assert "WCF" in indicators
    assert "WebForms" in indicators
    assert "System.Web" in indicators
    assert "Legacy Packages" in indicators
    assert "Config Complexity" in indicators

def test_json_serialization():
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(file_path="App.csproj", extension=".csproj", dependencies={"EntityFramework": "5.0.0"})
        ],
        technologies={".NET Framework (Legacy)"},
        dependencies={"EntityFramework": "5.0.0"}
    )
    
    engine = RiskEngine()
    report = engine.evaluate_project(analysis)
    
    # Convert to dictionary and verify it parses cleanly as JSON
    report_dict = report.to_dict()
    json_str = json.dumps(report_dict)
    loaded = json.loads(json_str)
    
    assert loaded["risk_score"] == report.risk_score
    assert loaded["risk_category"] == report.risk_category
    assert len(loaded["findings"]) == len(report.findings)
    assert loaded["legacy_packages"] == ["EntityFramework"]
