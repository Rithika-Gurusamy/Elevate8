import difflib
import time
from rich.console import Console
from rich.text import Text
from typing import Dict, List
from src.risk_engine.models import MigrationRiskReport
from src.ai_engine.models import ProjectMigrationSuggestion

class DiffGenerator:
    def __init__(self):
        self.html_diff_engine = difflib.HtmlDiff()

    def generate_unified_diff(self, original: str, modified: str, filename: str) -> str:
        """Generate a standard Git-style unified diff string."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "\n".join(diff)

    def generate_html_diff(self, original: str, modified: str, filename: str) -> str:
        """Generate a side-by-side HTML comparison of original vs modern .NET 8 equivalent."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Generates a complete standalone HTML document with side-by-side table
        return self.html_diff_engine.make_file(
            original_lines,
            modified_lines,
            fromdesc=f"Original {filename}",
            todesc=f"Modern .NET 8 equivalent"
        )

    def print_console_diff(self, original: str, modified: str, filename: str, console: Console = None):
        """Print a colorized git-style diff to the console using Rich."""
        if console is None:
            console = Console()

        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        diff_lines = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )

        console.print(f"\n[bold yellow]Diff Preview: {filename}[/bold yellow]")
        console.print("=" * 80)
        
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                console.print(Text(line, style="green"))
            elif line.startswith("-") and not line.startswith("---"):
                console.print(Text(line, style="red"))
            elif line.startswith("@@"):
                console.print(Text(line, style="cyan"))
            elif line.startswith("---") or line.startswith("+++"):
                console.print(Text(line, style="bold white"))
            else:
                console.print(line)
        console.print("=" * 80 + "\n")

    def generate_migration_report_markdown(
        self,
        project_path: str,
        risk_report: MigrationRiskReport,
        suggestions: ProjectMigrationSuggestion,
        original_contents: Dict[str, str]
    ) -> str:
        """Generate the full content of migration_report.md containing diffs and risk score."""
        md = []
        md.append(f"# Migration Assistant Report: {project_path}")
        md.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Risk Summary
        md.append("## 1. Executive Summary")
        md.append(f"- **Risk Score**: {risk_report.risk_score}/100")
        md.append(f"- **Complexity Category**: **{risk_report.risk_category}**")
        md.append(f"- **Total Legacy Files Identified**: {len(original_contents)}")
        md.append(f"- **Detected Legacy Technologies**: {', '.join(risk_report.legacy_packages) or 'None'}\n")

        # Findings
        md.append("## 2. Risk Engine Findings & Recommendations")
        for finding in risk_report.findings:
            md.append(f"### [{finding.impact}] {finding.indicator}")
            md.append(f"- **Occurrences**: {finding.count}")
            md.append(f"- **Remediation**: {finding.remediation}")
            md.append("- **Files impacted**:")
            for f in finding.files:
                md.append(f"  - `{f}`")
            md.append("")

        # Unsupported APIs
        if risk_report.unsupported_apis:
            md.append("## 3. Unsupported Legacy APIs")
            for api in risk_report.unsupported_apis:
                md.append(f"- `{api}`")
            md.append("")

        # Side-by-side / Unified Diff Previews
        md.append("## 4. File-by-File Migration Previews")
        
        for file_path, sug in suggestions.suggestions.items():
            md.append(f"### File: `{file_path}`")
            md.append(f"**Migration Strategy**: {sug.migration_strategy}\n")
            md.append(f"**API replacements needed**: {', '.join(sug.unsupported_apis) or 'None'}\n")
            
            # Embed modern code block
            md.append("**Migrated .NET 8 code equivalent**:")
            md.append("```csharp")
            md.append(sug.dotnet8_equivalent)
            md.append("```\n")

            # Embed git diff
            orig = original_contents.get(file_path, "")
            diff_str = self.generate_unified_diff(orig, sug.dotnet8_equivalent, file_path)
            md.append("**Git Diff preview**:")
            md.append("```diff")
            md.append(diff_str or "+ Whole file migrated / new code structure")
            md.append("```\n")
            md.append("---")

        return "\n".join(md)
