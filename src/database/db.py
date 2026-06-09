import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

class DatabaseManager:
    def __init__(self, db_path: str = "migration_assistant.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create the database schema if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # AI Response Cache Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_cache (
                    file_hash TEXT PRIMARY KEY,
                    prompt TEXT,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scan Runs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT,
                    files_count INTEGER,
                    complexity_score INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Risk Reports Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER,
                    risk_score INTEGER,
                    risk_category TEXT,
                    findings_json TEXT,
                    unsupported_apis_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(scan_run_id) REFERENCES scan_runs(id)
                )
            """)

            # Migration Reports Table (preserves backward compatibility)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT,
                    scan_run_id INTEGER,
                    report_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(scan_run_id) REFERENCES scan_runs(id)
                )
            """)

            # System/Migration Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Audit Trail Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(scan_run_id) REFERENCES scan_runs(id)
                )
            """)
            conn.commit()

    def get_cached_ai_response(self, file_hash: str) -> Optional[str]:
        """Retrieve cached AI response if it exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT response FROM ai_cache WHERE file_hash = ?", (file_hash,))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to query AI Cache: {str(e)}")
            return None

    def cache_ai_response(self, file_hash: str, prompt: str, response: str):
        """Save AI response into cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO ai_cache (file_hash, prompt, response, timestamp) VALUES (?, ?, ?, ?)",
                    (file_hash, prompt, response, datetime.now().isoformat())
                )
                conn.commit()
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to cache AI Response: {str(e)}")

    # Persistence APIs
    def save_scan_run(self, project_path: str, files_count: int, complexity_score: int) -> int:
        """Create a new scan run record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO scan_runs (project_path, files_count, complexity_score, timestamp) VALUES (?, ?, ?, ?)",
                    (project_path, files_count, complexity_score, datetime.now().isoformat())
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to save scan run: {str(e)}")
            return -1

    def save_risk_report(self, scan_run_id: int, risk_score: int, risk_category: str, findings: List[Any], unsupported_apis: List[str]) -> int:
        """Persist risk report assessment."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO risk_reports (scan_run_id, risk_score, risk_category, findings_json, unsupported_apis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (scan_run_id, risk_score, risk_category, json.dumps(findings), json.dumps(unsupported_apis), datetime.now().isoformat())
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to save risk report: {str(e)}")
            return -1

    def save_migration_report(self, project_path: str, report_json: str, scan_run_id: Optional[int] = None) -> int:
        """Save final migration report (supports both old and new signatures)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO migration_reports (project_path, scan_run_id, report_json, created_at) VALUES (?, ?, ?, ?)",
                    (project_path, scan_run_id, report_json, datetime.now().isoformat())
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to save migration report: {str(e)}")
            return -1

    def log_audit_action(self, scan_run_id: Optional[int], action: str, details: str) -> int:
        """Record user decisions or engine operations in the audit trail."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO audit_trail (scan_run_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                    (scan_run_id, action, details, datetime.now().isoformat())
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to write audit action: {str(e)}")
            return -1

    def log_message(self, level: str, message: str):
        """Write system log message."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO migration_logs (level, message, created_at) VALUES (?, ?, ?)",
                    (level, message, datetime.now().isoformat())
                )
                conn.commit()
        except sqlite3.Error:
            print(f"[{level}] {message}")

    # Query APIs
    def get_scan_runs(self) -> List[Dict[str, Any]]:
        """Retrieve all scan runs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, project_path, files_count, complexity_score, timestamp FROM scan_runs ORDER BY id DESC")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to query scan runs: {str(e)}")
            return []

    def get_risk_report_for_scan(self, scan_run_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve risk report associated with scan run id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, scan_run_id, risk_score, risk_category, findings_json, unsupported_apis_json, created_at FROM risk_reports WHERE scan_run_id = ?", (scan_run_id,))
                row = cursor.fetchone()
                if row:
                    res = dict(row)
                    res["findings"] = json.loads(res["findings_json"])
                    res["unsupported_apis"] = json.loads(res["unsupported_apis_json"])
                    return res
                return None
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to query risk report: {str(e)}")
            return None

    def get_migration_report_for_scan(self, scan_run_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve migration report associated with scan run id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, project_path, scan_run_id, report_json, created_at FROM migration_reports WHERE scan_run_id = ?", (scan_run_id,))
                row = cursor.fetchone()
                if row:
                    res = dict(row)
                    res["report"] = json.loads(res["report_json"])
                    return res
                return None
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to query migration report: {str(e)}")
            return None

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Retrieve audit log of user/migration decisions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, scan_run_id, action, details, timestamp FROM audit_trail ORDER BY id DESC")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Failed to query audit trail: {str(e)}")
            return []
