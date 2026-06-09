import os
import json
import pytest
from src.migration_engine.engine import MigrationEngine
from src.ai_engine.models import ProjectMigrationSuggestion, FileMigrationSuggestion

def test_migration_and_rollback_workflow(tmp_path):
    project_dir = str(tmp_path / "MyProject")
    os.makedirs(project_dir)

    # Create original files (using non-renamable CS and config files)
    file1_path = "MyClass.cs"
    file2_path = "SubFolder/SomeComponent.cs"
    
    full_file1_path = os.path.join(project_dir, file1_path)
    full_file2_path = os.path.join(project_dir, file2_path)
    
    os.makedirs(os.path.dirname(full_file2_path), exist_ok=True)
    
    with open(full_file1_path, "w", encoding="utf-8") as f:
        f.write("Original CS Content")
    with open(full_file2_path, "w", encoding="utf-8") as f:
        f.write("Original Component Content")

    # Suggestions setup
    suggestions = ProjectMigrationSuggestion(
        suggestions={
            file1_path: FileMigrationSuggestion(
                file_path=file1_path,
                summary="Migrated CS",
                migration_strategy="Upgrade CS",
                dotnet8_equivalent="New Migrated .NET 8 CS code"
            ),
            "Program.cs": FileMigrationSuggestion(
                file_path="Program.cs",
                summary="New program entry",
                migration_strategy="Create program",
                dotnet8_equivalent="WebApplication.CreateBuilder(args);"
            )
        }
    )

    engine = MigrationEngine()

    # 1. Test Backup Creation
    files_to_backup = [file1_path]
    backup_dir = engine.create_backup(project_dir, files_to_backup)
    
    assert os.path.exists(backup_dir)
    backup_file1 = os.path.join(backup_dir, file1_path)
    assert os.path.exists(backup_file1)
    with open(backup_file1, "r", encoding="utf-8") as f:
        assert f.read() == "Original CS Content"

    # 2. Test Apply Migration
    manifest_path = engine.apply_migrations(project_dir, suggestions, backup_dir)
    assert os.path.exists(manifest_path)

    # Check that file1 was modified in place
    with open(full_file1_path, "r", encoding="utf-8") as f:
        assert f.read() == "New Migrated .NET 8 CS code"

    # Check that Program.cs was created
    full_program_path = os.path.join(project_dir, "Program.cs")
    assert os.path.exists(full_program_path)
    with open(full_program_path, "r", encoding="utf-8") as f:
        assert f.read() == "WebApplication.CreateBuilder(args);"

    # Verify rollback_manifest contents
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
        assert len(manifest_data["files"]) == 2
        
        cs_entry = next(item for item in manifest_data["files"] if item["relative_path"] == "MyClass.cs")
        assert cs_entry["action"] == "MODIFY"
        assert cs_entry["before_version"] == "Original CS Content"
        assert cs_entry["after_version"] == "New Migrated .NET 8 CS code"
        
        prog_entry = next(item for item in manifest_data["files"] if item["relative_path"] == "Program.cs")
        assert prog_entry["action"] == "NEW"
        assert prog_entry["before_version"] == ""
        assert prog_entry["after_version"] == "WebApplication.CreateBuilder(args);"

    # 3. Test Undo Rollback
    result = engine.undo_migration(project_dir)
    assert result["success"] is True

    # Original CS content should be restored
    with open(full_file1_path, "r", encoding="utf-8") as f:
        assert f.read() == "Original CS Content"

    # Program.cs should be deleted
    assert not os.path.exists(full_program_path)

    # Manifest file should be removed
    assert not os.path.exists(manifest_path)


def test_migration_renaming_and_deleting_workflow(tmp_path):
    project_dir = str(tmp_path / "RenameDeleteProject")
    os.makedirs(project_dir)

    # Create original files
    aspx_path = "Pages/Main.aspx"
    aspx_cs_path = "Pages/Main.aspx.cs"
    svc_path = "Services/MyService.svc"
    web_config_path = "Web.config"
    
    full_aspx_path = os.path.join(project_dir, aspx_path)
    full_aspx_cs_path = os.path.join(project_dir, aspx_cs_path)
    full_svc_path = os.path.join(project_dir, svc_path)
    full_web_config_path = os.path.join(project_dir, web_config_path)

    os.makedirs(os.path.dirname(full_aspx_path), exist_ok=True)
    os.makedirs(os.path.dirname(full_svc_path), exist_ok=True)

    with open(full_aspx_path, "w", encoding="utf-8") as f:
        f.write("Original ASPX Markup")
    with open(full_aspx_cs_path, "w", encoding="utf-8") as f:
        f.write("Original ASPX Codebehind")
    with open(full_svc_path, "w", encoding="utf-8") as f:
        f.write("Original SVC Endpoint")
    with open(full_web_config_path, "w", encoding="utf-8") as f:
        f.write("Original Web Config XML")

    # Suggestions setup
    suggestions = ProjectMigrationSuggestion(
        suggestions={
            aspx_path: FileMigrationSuggestion(
                file_path=aspx_path,
                summary="Migrated ASPX",
                migration_strategy="Rename to razor",
                dotnet8_equivalent="<Page>Blazor Component Markup</Page>"
            ),
            aspx_cs_path: FileMigrationSuggestion(
                file_path=aspx_cs_path,
                summary="Delete codebehind",
                migration_strategy="Delete",
                dotnet8_equivalent=""
            ),
            svc_path: FileMigrationSuggestion(
                file_path=svc_path,
                summary="Delete SVC",
                migration_strategy="Delete",
                dotnet8_equivalent=""
            ),
            web_config_path: FileMigrationSuggestion(
                file_path=web_config_path,
                summary="Migrated web config",
                migration_strategy="Rename to appsettings",
                dotnet8_equivalent='{ "ConnectionStrings": {} }'
            )
        }
    )

    engine = MigrationEngine()

    # 1. Backup all original files
    files_to_backup = [aspx_path, aspx_cs_path, svc_path, web_config_path]
    backup_dir = engine.create_backup(project_dir, files_to_backup)

    assert os.path.exists(backup_dir)
    assert os.path.exists(os.path.join(backup_dir, aspx_path))
    assert os.path.exists(os.path.join(backup_dir, aspx_cs_path))
    assert os.path.exists(os.path.join(backup_dir, svc_path))
    assert os.path.exists(os.path.join(backup_dir, web_config_path))

    # 2. Apply migrations
    manifest_path = engine.apply_migrations(project_dir, suggestions, backup_dir)
    assert os.path.exists(manifest_path)

    # Verify original files are deleted from project root
    assert not os.path.exists(full_aspx_path)
    assert not os.path.exists(full_aspx_cs_path)
    assert not os.path.exists(full_svc_path)
    assert not os.path.exists(full_web_config_path)

    # Verify modern files are created in correct paths
    full_razor_path = os.path.join(project_dir, "Pages/Main.razor")
    full_appsettings_path = os.path.join(project_dir, "appsettings.json")
    
    assert os.path.exists(full_razor_path)
    assert os.path.exists(full_appsettings_path)
    
    with open(full_razor_path, "r", encoding="utf-8") as f:
        assert f.read() == "<Page>Blazor Component Markup</Page>"
    with open(full_appsettings_path, "r", encoding="utf-8") as f:
        assert f.read() == '{ "ConnectionStrings": {} }'

    # Verify manifest actions
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
        actions = {item["relative_path"]: item["action"] for item in manifest_data["files"]}
        
        assert actions["Pages/Main.aspx"] == "DELETE"
        assert actions["Pages/Main.aspx.cs"] == "DELETE"
        assert actions["Services/MyService.svc"] == "DELETE"
        assert actions["Web.config"] == "DELETE"
        
        assert actions["Pages/Main.razor"] == "NEW"
        assert actions["appsettings.json"] == "NEW"

    # 3. Test Rollback
    result = engine.undo_migration(project_dir)
    assert result["success"] is True

    # Check original files are restored
    assert os.path.exists(full_aspx_path)
    assert os.path.exists(full_aspx_cs_path)
    assert os.path.exists(full_svc_path)
    assert os.path.exists(full_web_config_path)

    with open(full_aspx_path, "r", encoding="utf-8") as f:
        assert f.read() == "Original ASPX Markup"
    with open(full_aspx_cs_path, "r", encoding="utf-8") as f:
        assert f.read() == "Original ASPX Codebehind"

    # Check modern files are deleted
    assert not os.path.exists(full_razor_path)
    assert not os.path.exists(full_appsettings_path)
    assert not os.path.exists(manifest_path)
