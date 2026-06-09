import pytest
from unittest.mock import MagicMock
from rich.console import Console
from src.reporting.diff_generator import DiffGenerator
from src.risk_engine.models import MigrationRiskReport
from src.ai_engine.models import ProjectMigrationSuggestion, FileMigrationSuggestion

def test_generate_unified_diff():
    original = "line 1\nline 2\nline 3"
    modified = "line 1\nline 2 modified\nline 3\nline 4"
    
    generator = DiffGenerator()
    diff_str = generator.generate_unified_diff(original, modified, "test.txt")
    
    assert "--- a/test.txt" in diff_str
    assert "+++ b/test.txt" in diff_str
    assert "-line 2" in diff_str
    assert "+line 2 modified" in diff_str
    assert "+line 4" in diff_str

def test_generate_html_diff():
    original = "line 1\nline 2"
    modified = "line 1\nline 2 modified"
    
    generator = DiffGenerator()
    html_str = generator.generate_html_diff(original, modified, "test.txt")
    
    assert "<html" in html_str.lower()
    assert "todesc" in html_str.lower() or "modern" in html_str.lower()
    assert "class=\"diff\"" in html_str.lower()

def test_print_console_diff():
    original = "line 1\nline 2"
    modified = "line 1\nline 2 modified"
    
    mock_console = MagicMock(spec=Console)
    generator = DiffGenerator()
    
    generator.print_console_diff(original, modified, "test.txt", console=mock_console)
    
    # Verify mock_console was called to print lines
    assert mock_console.print.called

def test_generate_markdown_report():
    project_path = "C:/MyOldApp"
    
    risk_report = MigrationRiskReport(
        risk_score=45,
        risk_category="Medium",
        findings=[],
        legacy_packages=["EntityFramework"],
        unsupported_apis=["System.Web"]
    )
    
    suggestions = ProjectMigrationSuggestion(
        suggestions={
            "web.config": FileMigrationSuggestion(
                file_path="web.config",
                summary="Old config file",
                migration_strategy="Convert to json",
                dotnet8_equivalent="{}"
            )
        }
    )
    
    original_contents = {"web.config": "<configuration></configuration>"}
    
    generator = DiffGenerator()
    report_md = generator.generate_migration_report_markdown(
        project_path,
        risk_report,
        suggestions,
        original_contents
    )
    
    assert "# Migration Assistant Report: C:/MyOldApp" in report_md
    assert "- **Complexity Category**: **Medium**" in report_md
    assert "EntityFramework" in report_md
    assert "System.Web" in report_md
    assert "web.config" in report_md
    assert "Convert to json" in report_md
