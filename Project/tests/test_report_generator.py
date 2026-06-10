import os
import pytest
import json
from src.scanner.models import ProjectAnalysis, AnalyzedFile
from src.risk_engine.models import MigrationRiskReport
from src.ai_engine.models import ProjectMigrationSuggestion, FileMigrationSuggestion
from src.reporting.generator import ReportGenerator

def test_effort_estimation():
    generator = ReportGenerator()
    assert "Low Effort" in generator.estimate_effort(25)
    assert "Medium Effort" in generator.estimate_effort(45)
    assert "High Effort" in generator.estimate_effort(75)
    assert "Critical" in generator.estimate_effort(90)

def test_json_and_markdown_exporters(tmp_path):
    project_path = "C:/DemoApp"
    
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(file_path="Service.svc", extension=".svc", lines_of_code=100)
        ]
    )
    
    risk_report = MigrationRiskReport(
        risk_score=50,
        risk_category="Medium",
        findings=[],
        legacy_packages=["WCF"],
        unsupported_apis=["System.ServiceModel"]
    )
    
    suggestions = ProjectMigrationSuggestion(
        suggestions={
            "Service.svc": FileMigrationSuggestion(
                file_path="Service.svc",
                summary="WCF Service",
                migration_strategy="Rewrite as Minimal API",
                dotnet8_equivalent="app.MapGet()",
                confidence_score=0.95
            )
        }
    )

    generator = ReportGenerator()
    
    # 1. JSON Report
    report_dict = generator.generate_json_report(project_path, risk_report, suggestions, analysis)
    assert report_dict["metadata"]["readiness_percentage"] == 50
    assert report_dict["metadata"]["total_files"] == 1
    assert "Service.svc" in report_dict["ai_suggestions"]
    
    json_out_path = tmp_path / "report.json"
    generator.export_json(report_dict, str(json_out_path))
    assert os.path.exists(json_out_path)
    
    with open(json_out_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["project_path"] == project_path

    # 2. Markdown Report
    original_contents = {"Service.svc": "<%@ ServiceHost %>"}
    report_md = generator.generate_markdown_report(project_path, risk_report, suggestions, original_contents)
    
    assert "# .NET 8 AI Migration Assistant Report" in report_md
    assert "**Migration Readiness**: `50%`" in report_md
    assert "Service.svc" in report_md
    assert "Rewrite as Minimal API" in report_md

def test_pdf_export(tmp_path):
    project_path = "C:/DemoApp"
    
    risk_report = MigrationRiskReport(
        risk_score=35,
        risk_category="Medium",
        findings=[],
        legacy_packages=[],
        unsupported_apis=[]
    )
    
    suggestions = ProjectMigrationSuggestion(
        suggestions={
            "app.config": FileMigrationSuggestion(
                file_path="app.config",
                summary="Config",
                migration_strategy="Convert to json",
                dotnet8_equivalent="{}"
            )
        }
    )
    
    pdf_out_path = tmp_path / "report.pdf"
    generator = ReportGenerator()
    
    success = generator.export_pdf(project_path, risk_report, suggestions, str(pdf_out_path))
    
    assert success is True
    assert os.path.exists(pdf_out_path)
    # Check that PDF has non-zero size
    assert os.path.getsize(pdf_out_path) > 0


def test_hidden_dependencies_in_report():
    from src.scanner.models import ProjectAnalysis, AnalyzedFile
    from src.risk_engine.models import MigrationRiskReport
    from src.ai_engine.models import ProjectMigrationSuggestion
    from src.reporting.generator import ReportGenerator

    project_path = "C:/DemoApp"
    
    # Setup mock analysis with direct assembly references (hidden dependencies)
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(file_path="LegacyApp.csproj", extension=".csproj", lines_of_code=10)
        ],
        dependencies={
            "AssemblyReference:System.Web.Extensions": "Local/GAC",
            "AssemblyReference:MyCompany.InternalHelper": "Local/GAC",
            "EntityFramework": "6.2.0"
        }
    )
    
    risk_report = MigrationRiskReport(
        risk_score=20,
        risk_category="Low",
        findings=[],
        legacy_packages=[],
        unsupported_apis=[]
    )
    
    suggestions = ProjectMigrationSuggestion(suggestions={})
    
    generator = ReportGenerator()
    report_dict = generator.generate_json_report(project_path, risk_report, suggestions, analysis)
    
    # Assert project_analysis key is present
    assert "project_analysis" in report_dict
    # Assert dependencies are successfully populated
    deps = report_dict["project_analysis"]["dependencies"]
    assert "AssemblyReference:System.Web.Extensions" in deps
    assert "AssemblyReference:MyCompany.InternalHelper" in deps
    assert deps["AssemblyReference:System.Web.Extensions"] == "Local/GAC"
