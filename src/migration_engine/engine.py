import os
import shutil
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.ai_engine.models import ProjectMigrationSuggestion

class MigrationEngine:
    def __init__(self, backups_root: str = "backups"):
        self.backups_root = backups_root

    def get_migrated_path(self, rel_path: str) -> Tuple[str, bool]:
        """
        Determine the migrated path and deletion rules for legacy files.
        Returns (new_rel_path, should_delete_original).
        If new_rel_path is empty, the file is deleted without a direct replacement.
        """
        lower_path = rel_path.lower()
        
        # Global.asax.cs -> Program.cs
        if "global.asax.cs" in lower_path:
            return "Program.cs", True
        # Global.asax -> Deleted
        elif "global.asax" in lower_path:
            return "", True
            
        # Web.config -> appsettings.json
        elif "web.config" in lower_path:
            return "appsettings.json", True
            
        # packages.config -> Deleted
        elif "packages.config" in lower_path:
            return "", True
            
        # Default.aspx -> Default.razor
        elif rel_path.endswith(".aspx"):
            return rel_path[:-5] + ".razor", True
            
        # Default.aspx.cs -> Deleted (logic merged into .razor)
        elif rel_path.endswith(".aspx.cs"):
            return "", True
            
        # Services/OrderService.svc -> Deleted
        elif rel_path.endswith(".svc") and not rel_path.endswith(".svc.cs"):
            return "", True
            
        # Services/OrderService.svc.cs -> Services/OrderService.cs
        elif rel_path.endswith(".svc.cs"):
            return rel_path[:-7] + ".cs", True
            
        # Default: modify in-place
        return rel_path, False

    def create_backup(self, project_path: str, files_to_backup: List[str]) -> str:
        """Create a timestamped backup folder and copy target files into it."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir_name = f"backup_{timestamp}"
        backup_dir_path = os.path.join(project_path, self.backups_root, backup_dir_name)
        
        os.makedirs(backup_dir_path, exist_ok=True)

        for rel_path in files_to_backup:
            src_path = os.path.join(project_path, rel_path)
            if os.path.exists(src_path):
                dest_path = os.path.join(backup_dir_path, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)

        return backup_dir_path

    def apply_migrations(
        self,
        project_path: str,
        suggestions: ProjectMigrationSuggestion,
        backup_dir_path: str
    ) -> str:
        """Apply AI suggestions, handle renames/deletions, and write rollback_manifest.json."""
        manifest_data = {
            "timestamp": datetime.now().isoformat(),
            "backup_dir": os.path.relpath(backup_dir_path, project_path),
            "files": []
        }

        # Track processed files to avoid duplicate work
        processed_deletions = set()

        for rel_path, sug in suggestions.suggestions.items():
            new_rel_path, should_delete_original = self.get_migrated_path(rel_path)

            # 1. Handle original file deletion
            if should_delete_original and rel_path not in processed_deletions:
                full_src_path = os.path.join(project_path, rel_path)
                original_content = ""
                if os.path.exists(full_src_path):
                    try:
                        with open(full_src_path, "r", encoding="utf-8") as f:
                            original_content = f.read()
                    except UnicodeDecodeError:
                        with open(full_src_path, "r", encoding="latin-1") as f:
                            original_content = f.read()
                    except Exception:
                        pass
                
                # Record deletion in manifest
                manifest_data["files"].append({
                    "relative_path": rel_path,
                    "action": "DELETE",
                    "before_version": original_content,
                    "after_version": ""
                })

                # Perform deletion
                if os.path.exists(full_src_path):
                    os.remove(full_src_path)
                processed_deletions.add(rel_path)

            # 2. Write to modern/new path
            if new_rel_path:
                full_dest_path = os.path.join(project_path, new_rel_path)
                
                # Determine action
                file_exists = os.path.exists(full_dest_path)
                action = "MODIFY" if file_exists else "NEW"

                # Read original content if file existed
                original_content = ""
                if file_exists:
                    try:
                        with open(full_dest_path, "r", encoding="utf-8") as f:
                            original_content = f.read()
                    except UnicodeDecodeError:
                        with open(full_dest_path, "r", encoding="latin-1") as f:
                            original_content = f.read()
                    except Exception:
                        pass

                # Record creation/modification in manifest
                manifest_data["files"].append({
                    "relative_path": new_rel_path,
                    "action": action,
                    "before_version": original_content,
                    "after_version": sug.dotnet8_equivalent
                })

                # Ensure parent directories exist
                os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)
                
                # Write the new C#/.razor/JSON content
                with open(full_dest_path, "w", encoding="utf-8") as f:
                    f.write(sug.dotnet8_equivalent)

        # Write manifest file to project root
        manifest_path = os.path.join(project_path, "rollback_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return manifest_path

    def undo_migration(self, project_path: str) -> Dict[str, Any]:
        """Undo a previously applied migration using the rollback manifest."""
        manifest_path = os.path.join(project_path, "rollback_manifest.json")
        if not os.path.exists(manifest_path):
            return {"success": False, "message": "No rollback_manifest.json found in project root."}

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            backup_dir_rel = manifest_data.get("backup_dir")
            backup_dir_path = os.path.join(project_path, backup_dir_rel)

            # Process files in reverse order to undo updates cleanly
            for file_entry in reversed(manifest_data.get("files", [])):
                rel_path = file_entry["relative_path"]
                action = file_entry["action"]
                full_dest_path = os.path.join(project_path, rel_path)

                if action == "MODIFY":
                    # Restore from backup folder
                    backup_file_path = os.path.join(backup_dir_path, rel_path)
                    if os.path.exists(backup_file_path):
                        os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)
                        shutil.copy2(backup_file_path, full_dest_path)
                    else:
                        # Fallback: rewrite using recorded 'before_version'
                        os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)
                        with open(full_dest_path, "w", encoding="utf-8") as f:
                            f.write(file_entry["before_version"])
                elif action == "NEW":
                    # Delete newly created files
                    if os.path.exists(full_dest_path):
                        os.remove(full_dest_path)
                elif action == "DELETE":
                    # Restore deleted files from backup folder
                    backup_file_path = os.path.join(backup_dir_path, rel_path)
                    if os.path.exists(backup_file_path):
                        os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)
                        shutil.copy2(backup_file_path, full_dest_path)
                    else:
                        # Fallback: rewrite using recorded 'before_version'
                        os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)
                        with open(full_dest_path, "w", encoding="utf-8") as f:
                            f.write(file_entry["before_version"])

            # Clean up manifest file
            os.remove(manifest_path)
            
            return {
                "success": True,
                "message": f"Successfully rolled back {len(manifest_data['files'])} files using backup."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to undo migration: {str(e)}"
            }
