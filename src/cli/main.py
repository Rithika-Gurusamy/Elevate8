"""
⚡ Legacy .NET Framework → .NET 8 AI Migration Assistant CLI
Enterprise-grade migration analysis, AI-powered suggestions, and automated code transformation.
"""
import os
import sys

# Add project root to sys.path to allow importing 'src' when running directly
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Reconfigure stdout/stderr on Windows to use UTF-8 and prevent cp1252 charmap encoding errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import typer
import subprocess
import time
import json
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.align import Align
import click
import typer.core

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Internal components
from src.database.db import DatabaseManager
from src.scanner.engine import ScannerEngine
from src.risk_engine.engine import RiskEngine
from src.ai_engine.client import GeminiClient
from src.reporting.diff_generator import DiffGenerator
from src.reporting.generator import ReportGenerator
from src.migration_engine.engine import MigrationEngine

__version__ = "1.0.0"

BANNER = r"""
[bold cyan]
  ╔═══════════════════════════════════════════════════════════════════╗
  ║                                                                   ║
  ║   ⚡  .NET Migration Assistant                                    ║
  ║   ───────────────────────────────                                  ║
  ║   Legacy .NET Framework  →  .NET 8                                ║
  ║   AI-Powered  ·  Enterprise-Grade  ·  Gemini-Driven               ║
  ║                                                                   ║
  ║   v{ver}                                                          ║
  ║                                                                   ║
  ╚═══════════════════════════════════════════════════════════════════╝
[/bold cyan]
""".replace("{ver}", __version__)


class DefaultGroup(typer.core.TyperGroup):
    """Custom Click group that defaults to the 'analyze' subcommand."""
    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if args and args[0] not in ["analyze", "rollback", "status"]:
                args.insert(0, "analyze")
            return super().resolve_command(ctx, args)


def version_callback(value: bool):
    if value:
        console = Console()
        console.print(f"[bold cyan]⚡ .NET Migration Assistant[/bold cyan] v{__version__}")
        raise typer.Exit()


app = typer.Typer(
    cls=DefaultGroup,
    help="⚡ Legacy .NET Framework → .NET 8 AI Migration Assistant CLI",
    rich_markup_mode="rich",
)
console = Console()


def _format_elapsed(seconds: float) -> str:
    """Format elapsed time in a human-readable way."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"


def _risk_color(score: int) -> str:
    """Return a Rich color string based on risk score."""
    if score <= 30:
        return "green"
    elif score <= 60:
        return "yellow"
    elif score <= 80:
        return "dark_orange"
    else:
        return "red"


def _risk_emoji(category: str) -> str:
    """Return emoji for risk category."""
    return {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🟠",
        "Critical": "🔴",
    }.get(category, "⚪")


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """⚡ Legacy .NET Framework → .NET 8 AI Migration Assistant"""
    pass


@app.command()
def analyze(
    project_path: str = typer.Argument(..., help="Local path to the legacy .NET project folder"),
    db_path: str = typer.Option("migration_assistant.db", "--db", help="Path to the SQLite database"),
    max_workers: int = typer.Option(4, "--workers", help="Concurrent threads for Gemini API calls"),
):
    """Scan a legacy project folder, assess risks, call Gemini AI, preview diffs, and migrate."""
    pipeline_start = time.time()
    timings: Dict[str, float] = {}

    # ── Banner ─────────────────────────────────────────────────────
    console.print(BANNER)

    # ── Validate ───────────────────────────────────────────────────
    if not os.path.exists(project_path):
        console.print(Panel(
            f"[bold red]Error:[/bold red] Directory [underline]{project_path}[/underline] does not exist.",
            border_style="red",
            title="⛔ Path Not Found",
        ))
        raise typer.Exit(code=1)

    project_path = os.path.abspath(project_path)

    db = DatabaseManager(db_path)
    scanner = ScannerEngine()
    risk_engine = RiskEngine()
    ai_client = GeminiClient(db)
    diff_gen = DiffGenerator()
    report_gen = ReportGenerator(diff_gen)
    migrator = MigrationEngine(backups_root=os.path.abspath("backups"))

    db.log_message("INFO", f"CLI started analysis for: {project_path}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 1: Scan Project
    # ══════════════════════════════════════════════════════════════
    console.print(Rule("[bold blue]Phase 1 · Project Scanner[/bold blue]", style="blue"))
    t0 = time.time()

    with Status("[bold yellow]Scanning project files recursively…[/bold yellow]", console=console, spinner="dots") as status:
        try:
            analysis = scanner.scan_directory(project_path)
        except Exception as e:
            console.print(f"[bold red]Scan failed:[/bold red] {str(e)}")
            db.log_message("ERROR", f"Scanning failed: {str(e)}")
            raise typer.Exit(code=1)

    timings["scan"] = time.time() - t0

    # Build a tree view of scanned files
    file_tree = Tree(f"[bold cyan]📁 {os.path.basename(project_path)}[/bold cyan]")
    ext_icons = {
        ".cs": "🔷", ".csproj": "📦", ".config": "⚙️",
        ".aspx": "🌐", ".asmx": "🌐", ".svc": "🔗",
        ".asax": "🏗️",
    }
    for f in analysis.files[:20]:
        icon = ext_icons.get(f.extension, "📄")
        patterns_str = ""
        if f.detected_patterns:
            tags = ", ".join(f.detected_patterns[:2])
            patterns_str = f" [dim]({tags})[/dim]"
        file_tree.add(f"{icon} [white]{f.file_path}[/white] [dim]{f.lines_of_code} LOC[/dim]{patterns_str}")
    if len(analysis.files) > 20:
        file_tree.add(f"[dim]… and {len(analysis.files) - 20} more files[/dim]")

    console.print(file_tree)
    console.print(f"[green]✓[/green] Scanned [bold]{len(analysis.files)}[/bold] files in [cyan]{_format_elapsed(timings['scan'])}[/cyan]\n")

    # ══════════════════════════════════════════════════════════════
    # PHASE 2: Risk Engine
    # ══════════════════════════════════════════════════════════════
    console.print(Rule("[bold blue]Phase 2 · Risk Engine[/bold blue]", style="blue"))
    t0 = time.time()

    with Status("[bold yellow]Evaluating migration risks…[/bold yellow]", console=console, spinner="dots"):
        risk_report = risk_engine.evaluate_project(analysis)
        scan_id = db.save_scan_run(project_path, len(analysis.files), analysis.complexity_score)
        db.save_risk_report(
            scan_id, risk_report.risk_score, risk_report.risk_category,
            risk_report.to_dict()["findings"], risk_report.unsupported_apis,
        )

    timings["risk"] = time.time() - t0

    score_color = _risk_color(risk_report.risk_score)
    emoji = _risk_emoji(risk_report.risk_category)

    risk_panel_text = (
        f"[bold]Risk Score:[/bold]  [{score_color}]{risk_report.risk_score}/100[/{score_color}]  {emoji}\n"
        f"[bold]Category:[/bold]   {risk_report.risk_category}\n"
        f"[bold]Blockers:[/bold]   {len(risk_report.findings)} detected\n"
        f"[bold]Readiness:[/bold]  {max(0, 100 - risk_report.risk_score)}%"
    )
    console.print(Panel(
        risk_panel_text,
        title="[bold]Risk Assessment[/bold]",
        border_style=score_color,
        padding=(1, 2),
    ))

    # Show findings table
    if risk_report.findings:
        findings_table = Table(
            title="Migration Blockers",
            header_style="bold magenta",
            border_style="dim",
            show_lines=True,
        )
        findings_table.add_column("Indicator", style="bold")
        findings_table.add_column("Impact", justify="center")
        findings_table.add_column("Count", justify="right")
        findings_table.add_column("Remediation", max_width=60)

        impact_colors = {"Critical": "red", "High": "dark_orange", "Medium": "yellow", "Low": "green"}
        for finding in risk_report.findings:
            ic = impact_colors.get(finding.impact, "white")
            findings_table.add_row(
                finding.indicator,
                f"[{ic}]{finding.impact}[/{ic}]",
                str(finding.count),
                finding.remediation[:80] + ("…" if len(finding.remediation) > 80 else ""),
            )
        console.print(findings_table)

    console.print(f"[green]✓[/green] Risk evaluation completed in [cyan]{_format_elapsed(timings['risk'])}[/cyan]\n")

    # ══════════════════════════════════════════════════════════════
    # PHASE 3: AI Suggestion Engine
    # ══════════════════════════════════════════════════════════════
    console.print(Rule("[bold blue]Phase 3 · Gemini AI Engine[/bold blue]", style="blue"))
    t0 = time.time()

    suggestions = None
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(description="[yellow]Generating AI migration suggestions…[/yellow]", total=None)
        try:
            suggestions = ai_client.analyze_project(project_path, analysis, risk_report, max_workers=max_workers)
            progress.update(task, completed=True, description="[green]✓ AI suggestion compilation complete![/green]")
        except Exception as e:
            console.print(f"[bold red]Gemini call failed:[/bold red] {str(e)}")
            db.log_message("ERROR", f"AI suggestions crashed: {str(e)}")
            raise typer.Exit(code=1)

    timings["ai"] = time.time() - t0

    if suggestions and suggestions.suggestions:
        ai_table = Table(
            title="AI Suggestions Summary",
            header_style="bold green",
            border_style="dim",
        )
        ai_table.add_column("File", style="cyan")
        ai_table.add_column("Strategy", max_width=50)
        ai_table.add_column("Confidence", justify="center")

        for fp, sug in suggestions.suggestions.items():
            conf = sug.confidence_score
            conf_color = "green" if conf >= 0.8 else ("yellow" if conf >= 0.5 else "red")
            
            # Safe normalization in case of anomalous strategy types
            strategy_str = sug.migration_strategy
            if isinstance(strategy_str, list):
                strategy_str = "\n".join(str(s) for s in strategy_str)
            elif strategy_str is None:
                strategy_str = ""
            else:
                strategy_str = str(strategy_str)

            ai_table.add_row(
                fp,
                strategy_str[:60] + ("…" if len(strategy_str) > 60 else ""),
                f"[{conf_color}]{conf*100:.0f}%[/{conf_color}]",
            )
        console.print(ai_table)

    console.print(f"[green]✓[/green] Generated [bold]{len(suggestions.suggestions) if suggestions else 0}[/bold] suggestions in [cyan]{_format_elapsed(timings['ai'])}[/cyan]\n")

    # ══════════════════════════════════════════════════════════════
    # PHASE 4: Diff Preview
    # ══════════════════════════════════════════════════════════════
    if suggestions and suggestions.suggestions:
        console.print(Rule("[bold blue]Phase 4 · Diff Preview[/bold blue]", style="blue"))
        for file_path, sug in list(suggestions.suggestions.items())[:2]:
            original_code = ""
            full_file_path = os.path.join(project_path, file_path)
            if os.path.exists(full_file_path):
                try:
                    with open(full_file_path, "r", encoding="utf-8") as f:
                        original_code = f.read()
                except Exception:
                    pass
            diff_gen.print_console_diff(original_code, sug.dotnet8_equivalent, file_path, console)
        if len(suggestions.suggestions) > 2:
            console.print(f"[dim]… and {len(suggestions.suggestions) - 2} more diff(s) available in dashboard.[/dim]\n")

    # Persist AI Suggestions in SQLite
    full_report_dict = report_gen.generate_json_report(project_path, risk_report, suggestions, analysis)
    json_report_str = json.dumps(full_report_dict)
    db.save_migration_report(project_path, json_report_str, scan_run_id=scan_id)

    # ══════════════════════════════════════════════════════════════
    # PHASE 5: Streamlit Dashboard
    # ══════════════════════════════════════════════════════════════
    console.print(Rule("[bold blue]Phase 5 · Dashboard[/bold blue]", style="blue"))
    console.print(Panel(
        "[bold]Launching the interactive Streamlit dashboard…[/bold]\n"
        "The dashboard will open in your default web browser.\n\n"
        "[yellow]Once you are done reviewing, press [bold]Enter[/bold] in the terminal to proceed to backups and migrations.[/yellow]",
        title="[bold blue]⚡ Streamlit Dashboard[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))
    db.log_message("INFO", "Launching Streamlit UI app from CLI.")

    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "src/ui/app.py", "--server.headless=true"]
        )
        # Give Streamlit a brief moment to spin up, bind the port and print URLs
        time.sleep(2.0)
    except Exception as e:
        console.print(f"[red]Could not start Streamlit: {str(e)}[/red]")

    try:
        console.input("\n👉 Press [bold green]Enter[/bold green] to take backup or save changes...")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Proceeding to backup and save changes...[/yellow]")

    if process:
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════
    # PHASE 6: Backup & Migration
    # ══════════════════════════════════════════════════════════════
    console.print(Rule("[bold blue]Phase 6 · Backup & Migration[/bold blue]", style="blue"))

    create_backup = typer.confirm("\nCreate timestamped backup before applying modifications?")
    backup_dir = None
    if create_backup:
        with Status("[bold green]Creating backup…[/bold green]", console=console):
            files_to_backup = list(suggestions.suggestions.keys())
            backup_dir = migrator.create_backup(project_path, files_to_backup)
            db.log_audit_action(scan_id, "BACKUP_CREATED", f"Backup directory: {backup_dir}")
        console.print(f"[green]✓[/green] Backup created successfully at: [underline]{backup_dir}[/underline]")
    else:
        console.print("[yellow]⚠ Skipped backup — overwriting without backup is risky.[/yellow]")

    apply_mig = typer.confirm("\nApply AI-generated migrations to source files?")
    if apply_mig:
        if not create_backup:
            console.print("[bold red]⛔ Safety constraint: backup required before overwriting.[/bold red]")
            typer.confirm("Create a backup now to proceed?", abort=True)
            with Status("[bold green]Creating backup…[/bold green]", console=console):
                files_to_backup = list(suggestions.suggestions.keys())
                backup_dir = migrator.create_backup(project_path, files_to_backup)
                db.log_audit_action(scan_id, "BACKUP_CREATED", f"Backup directory: {backup_dir}")
            console.print(f"[green]✓[/green] Backup created at: [underline]{backup_dir}[/underline]")

        t0 = time.time()
        with Status("[bold green]Applying migrations…[/bold green]", console=console):
            manifest_path = migrator.apply_migrations(project_path, suggestions, backup_dir)
            db.log_audit_action(scan_id, "MIGRATION_APPLIED", "Applied AI code transformations.")
        timings["migration"] = time.time() - t0
        console.print(f"[green]✓[/green] Code transformations written to files successfully!")
        console.print(f"[dim]Rollback manifest: {manifest_path}[/dim]")
    else:
        console.print("[yellow]Migration skipped — source files left unchanged.[/yellow]")

    # ══════════════════════════════════════════════════════════════
    # PHASE 7: Report Generation
    # ══════════════════════════════════════════════════════════════
    console.print(Rule("[bold blue]Phase 7 · Reports[/bold blue]", style="blue"))
    t0 = time.time()

    with Status("[bold yellow]Generating final reports…[/bold yellow]", console=console):
        original_contents = {}
        for path in suggestions.suggestions.keys():
            read_folder = backup_dir if (apply_mig and backup_dir) else project_path
            full_src_path = os.path.join(read_folder, path)
            if os.path.exists(full_src_path):
                try:
                    with open(full_src_path, "r", encoding="utf-8") as f:
                        original_contents[path] = f.read()
                except Exception:
                    original_contents[path] = ""

        # Markdown
        md_content = report_gen.generate_markdown_report(project_path, risk_report, suggestions, original_contents)
        md_report_path = os.path.join(project_path, "migration_report.md")
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # JSON
        json_report_path = os.path.join(project_path, "migration_report.json")
        report_gen.export_json(full_report_dict, json_report_path)

        # PDF
        pdf_report_path = os.path.join(project_path, "migration_report.pdf")
        pdf_success = report_gen.export_pdf(project_path, risk_report, suggestions, pdf_report_path)

    timings["reports"] = time.time() - t0

    # ══════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════
    total_elapsed = time.time() - pipeline_start
    timings["total"] = total_elapsed

    report_lines = [f"[green]✓[/green] [underline]{md_report_path}[/underline]  (Markdown)"]
    report_lines.append(f"[green]✓[/green] [underline]{json_report_path}[/underline]  (JSON)")
    if pdf_success:
        report_lines.append(f"[green]✓[/green] [underline]{pdf_report_path}[/underline]  (PDF)")

    summary_text = (
        f"[bold green]✔ Migration Analysis Complete[/bold green]\n\n"
        f"[bold]Project:[/bold]     {os.path.basename(project_path)}\n"
        f"[bold]Files:[/bold]       {len(analysis.files)} scanned\n"
        f"[bold]Risk Score:[/bold]  [{score_color}]{risk_report.risk_score}/100[/{score_color}] ({risk_report.risk_category})\n"
        f"[bold]Suggestions:[/bold] {len(suggestions.suggestions) if suggestions else 0} generated\n"
        f"[bold]Readiness:[/bold]   {max(0, 100 - risk_report.risk_score)}%\n\n"
        f"[bold]Reports:[/bold]\n" + "\n".join(f"  {l}" for l in report_lines) + "\n\n"
        f"[bold]Timing:[/bold]\n"
        f"  Scan: {_format_elapsed(timings.get('scan', 0))}  ·  "
        f"Risk: {_format_elapsed(timings.get('risk', 0))}  ·  "
        f"AI: {_format_elapsed(timings.get('ai', 0))}  ·  "
        f"Reports: {_format_elapsed(timings.get('reports', 0))}\n"
        f"  [bold cyan]Total: {_format_elapsed(total_elapsed)}[/bold cyan]"
    )

    console.print()
    console.print(Panel(
        summary_text,
        title="[bold]⚡ Pipeline Summary[/bold]",
        border_style="green",
        padding=(1, 3),
    ))
    db.log_message("INFO", f"CLI migration run complete in {_format_elapsed(total_elapsed)}.")


@app.command()
def rollback(
    project_path: str = typer.Argument(..., help="Local path to the legacy .NET project folder"),
    db_path: str = typer.Option("migration_assistant.db", "--db", help="Path to the SQLite database"),
):
    """Undo a previously applied migration using the rollback manifest."""
    console.print(BANNER)
    console.print(f"Executing rollback for project: {project_path}")

    db = DatabaseManager(db_path)
    db.log_message("INFO", f"CLI started rollback for: {project_path}")

    migrator = MigrationEngine(backups_root=os.path.abspath("backups"))
    result = migrator.undo_migration(project_path)

    if result["success"]:
        console.print(Panel(
            f"[bold green]Rollback Successful[/bold green]\n\n{result['message']}",
            border_style="green",
            title="✓ Rollback",
        ))
        db.log_message("INFO", f"Rollback successful: {result['message']}")
    else:
        console.print(Panel(
            f"[bold red]Rollback Failed[/bold red]\n\n{result['message']}",
            border_style="red",
            title="⛔ Rollback Error",
        ))
        db.log_message("ERROR", f"Rollback failed: {result['message']}")
        raise typer.Exit(code=1)


@app.command()
def status(
    db_path: str = typer.Option("migration_assistant.db", "--db", help="Path to the SQLite database"),
):
    """Show the last scan summary from the database."""
    console.print(BANNER)

    db = DatabaseManager(db_path)
    runs = db.get_scan_runs()

    if not runs:
        console.print("[yellow]No scan history found. Run 'analyze' first.[/yellow]")
        raise typer.Exit()

    latest = runs[0]
    risk = db.get_risk_report_for_scan(latest["id"])

    console.print(Panel(
        f"[bold]Last Scan:[/bold]       {latest['project_path']}\n"
        f"[bold]Timestamp:[/bold]       {latest['timestamp']}\n"
        f"[bold]Files Scanned:[/bold]   {latest['files_count']}\n"
        f"[bold]Complexity:[/bold]      {latest['complexity_score']}\n"
        + (
            f"[bold]Risk Score:[/bold]     [{_risk_color(risk['risk_score'])}]{risk['risk_score']}/100[/{_risk_color(risk['risk_score'])}]\n"
            f"[bold]Risk Category:[/bold]  {risk['risk_category']}\n"
            f"[bold]Readiness:[/bold]      {max(0, 100 - risk['risk_score'])}%"
            if risk else "[dim]No risk report found.[/dim]"
        ),
        title="[bold]⚡ Last Scan Status[/bold]",
        border_style="cyan",
        padding=(1, 2),
    ))

    # Show scan history
    if len(runs) > 1:
        history_table = Table(title="Scan History", header_style="bold cyan", border_style="dim")
        history_table.add_column("#", justify="right")
        history_table.add_column("Project")
        history_table.add_column("Files", justify="right")
        history_table.add_column("Timestamp")

        for run in runs[:10]:
            history_table.add_row(str(run["id"]), os.path.basename(run["project_path"]), str(run["files_count"]), run["timestamp"][:19])
        console.print(history_table)


if __name__ == "__main__":
    app()
