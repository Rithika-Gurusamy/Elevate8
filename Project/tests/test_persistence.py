import pytest
import os
import json
from src.database.db import DatabaseManager

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "persistence.db"
    return DatabaseManager(str(db_file))

def test_scan_runs_persistence(test_db):
    project_path = "C:/DemoApps/LegacyApp"
    
    # Save scan run
    scan_id = test_db.save_scan_run(project_path, 15, 80)
    assert scan_id > 0
    
    # Query scan runs
    runs = test_db.get_scan_runs()
    assert len(runs) == 1
    assert runs[0]["id"] == scan_id
    assert runs[0]["project_path"] == project_path
    assert runs[0]["files_count"] == 15
    assert runs[0]["complexity_score"] == 80

def test_risk_reports_persistence(test_db):
    # Setup scan run parent
    scan_id = test_db.save_scan_run("C:/DemoApps/LegacyApp", 5, 40)
    
    findings = [
        {"indicator": "WCF", "count": 2, "remediation": "Migrate to gRPC"}
    ]
    unsupported = ["System.ServiceModel"]
    
    # Save risk report
    risk_id = test_db.save_risk_report(scan_id, 45, "Medium", findings, unsupported)
    assert risk_id > 0
    
    # Query risk report
    report = test_db.get_risk_report_for_scan(scan_id)
    assert report is not None
    assert report["id"] == risk_id
    assert report["risk_score"] == 45
    assert report["risk_category"] == "Medium"
    assert report["findings"][0]["indicator"] == "WCF"
    assert "System.ServiceModel" in report["unsupported_apis"]

def test_migration_reports_persistence(test_db):
    scan_id = test_db.save_scan_run("C:/DemoApps/LegacyApp", 5, 40)
    report_payload = {"summary": "Migration Suggestion payload"}
    
    # Save migration report
    rep_id = test_db.save_migration_report("C:/DemoApps/LegacyApp", json.dumps(report_payload), scan_run_id=scan_id)
    assert rep_id > 0
    
    # Query migration report
    mig_report = test_db.get_migration_report_for_scan(scan_id)
    assert mig_report is not None
    assert mig_report["id"] == rep_id
    assert mig_report["report"]["summary"] == "Migration Suggestion payload"

def test_audit_trail_persistence(test_db):
    scan_id = test_db.save_scan_run("C:/DemoApps/LegacyApp", 5, 40)
    
    # Log audit actions
    audit_id1 = test_db.log_audit_action(scan_id, "BACKUP_CREATED", "Backup saved to folder C:/Backups/123")
    audit_id2 = test_db.log_audit_action(scan_id, "MIGRATION_APPLIED", "Applied AI suggestions to 2 files")
    
    assert audit_id1 > 0
    assert audit_id2 > 0
    
    # Query audit trail
    trail = test_db.get_audit_trail()
    assert len(trail) == 2
    
    # Ordered DESC by default (most recent first)
    assert trail[0]["action"] == "MIGRATION_APPLIED"
    assert trail[1]["action"] == "BACKUP_CREATED"
    assert trail[1]["scan_run_id"] == scan_id
