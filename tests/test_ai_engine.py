import sys
from unittest.mock import MagicMock, patch

# Mock google.generativeai module to avoid missing dependency during tests
sys.modules['google.generativeai'] = MagicMock()

import pytest
import json
from src.database.db import DatabaseManager
from src.scanner.models import ProjectAnalysis, AnalyzedFile
from src.risk_engine.models import MigrationRiskReport
from src.ai_engine.client import GeminiClient
from src.ai_engine.models import FileMigrationSuggestion

@pytest.fixture
def mock_db(tmp_path):
    db_file = tmp_path / "test_cache.db"
    return DatabaseManager(str(db_file))

def test_mock_mode_when_no_api_key(mock_db):
    client = GeminiClient(db_manager=mock_db, api_key=None)
    
    suggestion = client.get_migration_suggestion(
        file_path="Service.svc",
        content="ServiceContract",
        technology="WCF",
        findings=["Legacy WCF service"]
    )
    
    assert suggestion.file_path == "Service.svc"
    assert "gRPC" in suggestion.migration_strategy
    assert "Minimal API" in suggestion.dotnet8_equivalent
    assert suggestion.confidence_score == 0.8

def test_cache_hit_avoids_api_call(mock_db):
    # Compute the expected hash
    client = GeminiClient(db_manager=mock_db, api_key="dummy_key")
    file_path = "app.config"
    content = "connectionStrings"
    technology = "XML Configuration"
    findings = ["Legacy config"]
    
    file_hash = client._compute_hash(file_path, content, technology, findings)
    
    # Store mocked response in database cache
    cached_data = {
        "summary": "Cached summary",
        "migration_strategy": "Cached strategy",
        "unsupported_apis": ["system.config"],
        "dotnet8_equivalent": "Cached dotnet8 code",
        "code_diff_markdown": "Cached diff",
        "confidence_score": 0.99
    }
    mock_db.cache_ai_response(file_hash, "Dummy prompt", json.dumps(cached_data))

    # Mock the generative model to ensure it is NEVER called
    mock_model = MagicMock()
    client.model = mock_model

    suggestion = client.get_migration_suggestion(file_path, content, technology, findings)
    
    # Assertions
    mock_model.generate_content.assert_not_called()
    assert suggestion.file_path == file_path
    assert suggestion.summary == "Cached summary"
    assert suggestion.confidence_score == 0.99

@patch("google.generativeai.GenerativeModel")
def test_api_call_and_caching(mock_gen_model_class, mock_db):
    # Setup mock return value for model
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    
    api_response_data = {
        "summary": "API summary",
        "migration_strategy": "API strategy",
        "unsupported_apis": ["WCF.Legacy"],
        "dotnet8_equivalent": "API equivalent code",
        "code_diff_markdown": "API diff",
        "confidence_score": 0.92
    }
    mock_response.text = json.dumps(api_response_data)
    mock_model_instance.generate_content.return_value = mock_response
    
    client = GeminiClient(db_manager=mock_db, api_key="dummy_key")
    client.model = mock_model_instance
    
    file_path = "Service.svc"
    content = "ServiceContract"
    technology = "WCF"
    findings = ["WCF Service Contract"]
    
    # Ensure cache is empty
    file_hash = client._compute_hash(file_path, content, technology, findings)
    assert mock_db.get_cached_ai_response(file_hash) is None

    # Call method
    suggestion = client.get_migration_suggestion(file_path, content, technology, findings)
    
    # Verify mock calls
    mock_model_instance.generate_content.assert_called_once()
    
    # Verify result
    assert suggestion.summary == "API summary"
    assert suggestion.confidence_score == 0.92
    
    # Verify it is now cached in DB
    cached_val = mock_db.get_cached_ai_response(file_hash)
    assert cached_val is not None
    assert json.loads(cached_val)["summary"] == "API summary"

@patch("google.generativeai.GenerativeModel")
def test_api_retry_logic(mock_gen_model_class, mock_db):
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    
    api_response_data = {
        "summary": "Success after retry",
        "migration_strategy": "Retry strategy",
        "unsupported_apis": [],
        "dotnet8_equivalent": "",
        "code_diff_markdown": "",
        "confidence_score": 0.9
    }
    mock_response.text = json.dumps(api_response_data)
    
    # Raise error on first call, succeed on second call
    mock_model_instance.generate_content.side_effect = [Exception("API Throttled"), mock_response]
    
    client = GeminiClient(db_manager=mock_db, api_key="dummy_key")
    client.model = mock_model_instance
    
    suggestion = client.get_migration_suggestion(
        file_path="app.config",
        content="connectionStrings",
        technology="XML Configuration",
        findings=[],
        max_retries=3,
        backoff_factor=0.1  # Fast backoff for testing
    )
    
    # Verify it was called twice
    assert mock_model_instance.generate_content.call_count == 2
    assert suggestion.summary == "Success after retry"

def test_batch_project_analysis(mock_db, tmp_path):
    # Write a dummy config file
    config_file = tmp_path / "web.config"
    config_file.write_text("<configuration><system.web></system.web></configuration>")
    
    analysis = ProjectAnalysis(
        files=[
            AnalyzedFile(file_path="web.config", extension=".config", detected_patterns=["Legacy <system.web> Configuration"])
        ],
        technologies={"ASP.NET Legacy"},
        dependencies={}
    )
    
    risk_report = MigrationRiskReport(
        risk_score=15,
        risk_category="Low",
        findings=[
            MagicMock(indicator="Config Complexity", files=["web.config"], remediation="Migrate to appsettings.json")
        ]
    )
    
    # Run client in mock mode
    client = GeminiClient(db_manager=mock_db, api_key=None)
    
    proj_suggestion = client.analyze_project(
        project_dir=str(tmp_path),
        analysis=analysis,
        risk_report=risk_report,
        max_workers=2
    )
    
    assert "web.config" in proj_suggestion.suggestions
    assert "Logging" in proj_suggestion.suggestions["web.config"].dotnet8_equivalent
