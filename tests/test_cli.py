import pytest
import os
import json
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from src.cli.main import app
from src.scanner.models import ProjectAnalysis, AnalyzedFile
from src.risk_engine.models import MigrationRiskReport, RiskFinding
from src.ai_engine.models import ProjectMigrationSuggestion, FileMigrationSuggestion

runner = CliRunner()

@pytest.fixture
def mock_pipeline_data():
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(file_path="Service.svc", extension=".svc", lines_of_code=50)
        ],
        technologies={"WCF"},
        dependencies={}
    )
    
    risk_report = MigrationRiskReport(
        risk_score=30,
        risk_category="Low",
        findings=[
            RiskFinding(indicator="WCF", impact="High", count=1, files=["Service.svc"], remediation="gRPC")
        ]
    )
    
    suggestions = ProjectMigrationSuggestion(
        suggestions={
            "Service.svc": FileMigrationSuggestion(
                file_path="Service.svc",
                summary="WCF svc file",
                migration_strategy="Rewrite as Minimal API",
                dotnet8_equivalent="app.MapGet()",
                confidence_score=0.9
            )
        }
    )
    return analysis, risk_report, suggestions

@patch("src.cli.main.subprocess.run")
@patch("src.cli.main.ScannerEngine.scan_directory")
@patch("src.cli.main.RiskEngine.evaluate_project")
@patch("src.cli.main.GeminiClient.analyze_project")
def test_cli_analyze_flow(
    mock_ai_analyze,
    mock_risk_evaluate,
    mock_scan_dir,
    mock_sub_run,
    mock_pipeline_data,
    tmp_path
):
    analysis, risk_report, suggestions = mock_pipeline_data
    
    # Setup mocks
    mock_scan_dir.return_value = analysis
    mock_risk_evaluate.return_value = risk_report
    mock_ai_analyze.return_value = suggestions
    mock_sub_run.return_value = MagicMock()  # Mock Streamlit run
    
    # Setup mock project dir
    proj_dir = tmp_path / "MyLegacyProject"
    os.makedirs(proj_dir)
    (proj_dir / "Service.svc").write_text("<%@ ServiceHost %>")
    
    db_file = tmp_path / "cli_test.db"
    
    result = runner.invoke(app, [
        str(proj_dir),
        "--db", str(db_file)
    ], input="y\ny\n")
    
    # Assertions
    if result.exit_code != 0:
        print("CLI OUTPUT:", result.output)
        print("CLI EXCEPTION:", result.exception)
    assert result.exit_code == 0
    assert "Risk Assessment" in result.output
    assert "Project Scanner" in result.output
    assert "AI suggestion compilation complete!" in result.output
    assert "Diff Preview" in result.output
    assert "Backup created successfully" in result.output
    assert "Code transformations written to files" in result.output
    
    # Verify report files created in project dir
    assert os.path.exists(proj_dir / "migration_report.md")
    assert os.path.exists(proj_dir / "migration_report.json")
    assert os.path.exists(proj_dir / "migration_report.pdf")
    assert os.path.exists(proj_dir / "rollback_manifest.json")

@patch("src.cli.main.MigrationEngine.undo_migration")
def test_cli_rollback_flow(mock_undo, tmp_path):
    mock_undo.return_value = {"success": True, "message": "Rolled back successfully"}
    
    proj_dir = tmp_path / "MyProject"
    os.makedirs(proj_dir)
    db_file = tmp_path / "cli_test.db"
    
    result = runner.invoke(app, [
        "rollback",
        str(proj_dir),
        "--db", str(db_file)
    ])
    
    if result.exit_code != 0:
        print("ROLLBACK OUTPUT:", result.output)
        print("ROLLBACK EXCEPTION:", result.exception)
    assert result.exit_code == 0
    assert "Executing rollback for project" in result.output
    assert "Rollback Successful" in result.output
    mock_undo.assert_called_once_with(str(proj_dir))
