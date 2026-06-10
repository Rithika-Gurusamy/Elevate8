import pytest
import sqlite3
import json
import os
from unittest.mock import patch
from src.ui.app import load_latest_report, load_all_reports, load_report_by_id, load_logs

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_app.db"
    # Create schema
    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE migration_reports (id INTEGER PRIMARY KEY, project_path TEXT, report_json TEXT, created_at TEXT)")
        cursor.execute("CREATE TABLE migration_logs (id INTEGER PRIMARY KEY, level TEXT, message TEXT, created_at TEXT)")
        
        # Insert report
        cursor.execute(
            "INSERT INTO migration_reports (id, project_path, report_json, created_at) VALUES (?, ?, ?, ?)",
            (1, "C:/Path/To/Project", json.dumps({"risk_report": {"risk_score": 10}}), "2026-06-09T00:00:00")
        )
        
        # Insert log
        cursor.execute(
            "INSERT INTO migration_logs (id, level, message, created_at) VALUES (?, ?, ?, ?)",
            (1, "INFO", "Started test scan", "2026-06-09T00:00:00")
        )
        conn.commit()
    return str(db_file)

def test_db_loaders(temp_db):
    # Patch the DB_PATH in app.py to point to temp_db
    with patch("src.ui.app.DB_PATH", temp_db):
        latest = load_latest_report()
        assert latest is not None
        assert latest["id"] == 1
        assert latest["project_path"] == "C:/Path/To/Project"
        assert latest["report"]["risk_report"]["risk_score"] == 10
        
        all_rep = load_all_reports()
        assert len(all_rep) == 1
        assert all_rep[0]["id"] == 1
        
        by_id = load_report_by_id(1)
        assert by_id is not None
        assert by_id["project_path"] == "C:/Path/To/Project"
        
        logs = load_logs()
        assert len(logs) == 1
        assert logs[0][0] == "INFO"
        assert logs[0][1] == "Started test scan"
