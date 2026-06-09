import os
import json
import time
from typing import Dict, Any, List
from src.scanner.models import ProjectAnalysis
from src.risk_engine.models import MigrationRiskReport
from src.ai_engine.models import ProjectMigrationSuggestion

# ReportLab imports (guarded)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    reportlab_installed = True
except ImportError:
    reportlab_installed = False

class ReportGenerator:
    def __init__(self, diff_generator=None):
        self.diff_generator = diff_generator
        if not self.diff_generator:
            from src.reporting.diff_generator import DiffGenerator
            self.diff_generator = DiffGenerator()

    def estimate_effort(self, risk_score: int) -> str:
        """Estimate the migration effort based on risk score."""
        if risk_score <= 30:
            return "1-3 Days (Low Effort)"
        elif risk_score <= 60:
            return "5-10 Days (Medium Effort)"
        elif risk_score <= 80:
            return "2-4 Weeks (High Effort)"
        else:
            return "1-3 Months (Critical Refactoring)"

    def generate_json_report(
        self,
        project_path: str,
        risk_report: MigrationRiskReport,
        suggestions: ProjectMigrationSuggestion,
        analysis: ProjectAnalysis
    ) -> Dict[str, Any]:
        """Compile a complete JSON-serializable report object."""
        readiness = max(0, 100 - risk_report.risk_score)
        effort = self.estimate_effort(risk_report.risk_score)
        
        # Build raw dict structure
        report_dict = {
            "metadata": {
                "project_path": project_path,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "estimated_effort": effort,
                "readiness_percentage": readiness,
                "total_files": len(analysis.files)
            },
            "risk_report": risk_report.to_dict(),
            "ai_suggestions": suggestions.to_dict(),
            "project_analysis": {
                "dependencies": analysis.dependencies,
                "detected_patterns": analysis.detected_patterns
            }
        }
        return report_dict

    def export_json(self, report_dict: Dict[str, Any], output_path: str):
        """Save report dict to a JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)

    def generate_markdown_report(
        self,
        project_path: str,
        risk_report: MigrationRiskReport,
        suggestions: ProjectMigrationSuggestion,
        original_contents: Dict[str, str]
    ) -> str:
        """Generate a complete Markdown report combining roadmap, AI suggestions, and diffs."""
        readiness = max(0, 100 - risk_report.risk_score)
        effort = self.estimate_effort(risk_report.risk_score)
        
        md = []
        md.append(f"# .NET 8 AI Migration Assistant Report")
        md.append(f"**Target Project**: `{project_path}`  ")
        md.append(f"**Report Generated**: `{time.strftime('%Y-%m-%d %H:%M:%S')}`  ")
        md.append(f"**Migration Readiness**: `{readiness}%`  ")
        md.append(f"**Overall Risk Rating**: `{risk_report.risk_category} ({risk_report.risk_score}/100)`  ")
        md.append(f"**Estimated Migration Effort**: `{effort}`  \n")
        
        md.append("## 1. Executive Summary")
        md.append("This report summarizes the scans and risk assessments of porting the legacy .NET project to modern .NET 8. ")
        md.append(f"Out of the files analyzed, we identified several structural migration barriers including WCF, WebForms, or outdated package dependencies.")
        md.append("\n")

        # Roadmap
        md.append("## 2. Migration Roadmap")
        md.append("To migrate this project to .NET 8, the following roadmap is recommended:")
        md.append("1. **Preparation**: Create a full backup of the source codebase.")
        md.append("2. **Infrastructure**: Upgrade the project SDK version in `.csproj` files to target `net8.0` and clean up configuration files.")
        md.append("3. **Dependency Cleanup**: Replace or upgrade unsupported NuGet packages (e.g. migrate EntityFramework to EF Core).")
        md.append("4. **Service Rewrite**: Migrate legacy endpoints (e.g., WCF services to gRPC/Minimal APIs, and WebForms UI pages to Blazor or Razor Pages).")
        md.append("5. **Validation**: Execute integration and build validation pipelines.")
        md.append("\n")

        # Risk Analysis
        md.append("## 3. Risk Assessment & Blockers")
        for finding in risk_report.findings:
            md.append(f"### [{finding.impact} Risk] {finding.indicator}")
            md.append(f"- **Occurrences**: {finding.count}")
            md.append(f"- **Remediation Recommendation**: {finding.remediation}")
            md.append("- **Impacted Files**:")
            for f in finding.files:
                md.append(f"  - `{f}`")
            md.append("")
        md.append("\n")

        # Unsupported APIs
        if risk_report.unsupported_apis:
            md.append("## 4. Unsupported Legacy APIs")
            for api in risk_report.unsupported_apis:
                md.append(f"- `{api}`")
            md.append("")
        md.append("\n")

        # AI Recommendations & Diff Summaries
        md.append("## 5. File-by-File AI Suggestions & Diffs")
        for file_path, sug in suggestions.suggestions.items():
            md.append(f"### File: `{file_path}`")
            md.append(f"**Summary**: {sug.summary}  ")
            md.append(f"**Migration Plan**: {sug.migration_strategy}  ")
            md.append(f"**AI Confidence**: `{sug.confidence_score * 100:.1f}%`  \n")
            
            # Code diff block
            orig = original_contents.get(file_path, "")
            diff_str = self.diff_generator.generate_unified_diff(orig, sug.dotnet8_equivalent, file_path)
            md.append("**Git Diff Summary**:")
            md.append("```diff")
            md.append(diff_str or "+ Whole file migrated / new code structure")
            md.append("```\n")
            md.append("---")
            
        return "\n".join(md)

    def export_pdf(
        self,
        project_path: str,
        risk_report: MigrationRiskReport,
        suggestions: ProjectMigrationSuggestion,
        output_path: str
    ) -> bool:
        """Export report to a professional styled PDF using ReportLab."""
        if not reportlab_installed:
            # ReportLab not loaded
            return False

        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=54,
                leftMargin=54,
                topMargin=54,
                bottomMargin=54
            )
            
            styles = getSampleStyleSheet()
            
            # Custom Styles
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontSize=24,
                leading=28,
                textColor=colors.HexColor('#0f2d59'),
                spaceAfter=15
            )
            
            h2_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=16,
                leading=20,
                textColor=colors.HexColor('#1f6feb'),
                spaceBefore=15,
                spaceAfter=10
            )

            h3_style = ParagraphStyle(
                'SubSectionHeader',
                parent=styles['Heading3'],
                fontSize=12,
                leading=16,
                textColor=colors.HexColor('#0d1117'),
                spaceBefore=8,
                spaceAfter=4
            )
            
            body_style = ParagraphStyle(
                'ReportBody',
                parent=styles['BodyText'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#24292f'),
                spaceAfter=8
            )

            code_style = ParagraphStyle(
                'CodeSnippet',
                parent=styles['Code'],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor('#032f62'),
                backColor=colors.HexColor('#f6f8fa'),
                borderColor=colors.HexColor('#d0d7de'),
                borderWidth=1,
                borderPadding=6,
                spaceAfter=10
            )

            story = []

            # 1. Document Title
            story.append(Paragraph("⚡ .NET 8 AI Migration Assistant Report", title_style))
            story.append(Spacer(1, 10))
            
            # Metadata Grid
            readiness = max(0, 100 - risk_report.risk_score)
            effort = self.estimate_effort(risk_report.risk_score)
            
            metadata_table_data = [
                [Paragraph("<b>Project:</b>", body_style), Paragraph(os.path.basename(project_path), body_style)],
                [Paragraph("<b>Path:</b>", body_style), Paragraph(project_path, body_style)],
                [Paragraph("<b>Generated at:</b>", body_style), Paragraph(time.strftime('%Y-%m-%d %H:%M:%S'), body_style)],
                [Paragraph("<b>Overall Risk Rating:</b>", body_style), Paragraph(f"<b>{risk_report.risk_category}</b> ({risk_report.risk_score}/100)", body_style)],
                [Paragraph("<b>Migration Readiness:</b>", body_style), Paragraph(f"{readiness}%", body_style)],
                [Paragraph("<b>Estimated Effort:</b>", body_style), Paragraph(effort, body_style)]
            ]
            
            t = Table(metadata_table_data, colWidths=[130, 350])
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d7de')),
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f6f8fa')),
                ('PADDING', (0,0), (-1,-1), 6),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t)
            story.append(Spacer(1, 20))

            # 2. Executive Summary
            story.append(Paragraph("1. Executive Summary", h2_style))
            story.append(Paragraph(
                f"This migration report evaluates the structure, dependencies, and code configuration of the application "
                f"located at {project_path}. The assistant scanned legacy codebases, computed risk scores, and generated "
                f"remediation strategies using Gemini models.", body_style
            ))
            
            # 3. Roadmap
            story.append(Paragraph("2. Migration Roadmap", h2_style))
            roadmap_points = [
                "<b>Phase 1: Project Preparation</b> - Create full system backups and code checkpoints.",
                "<b>Phase 2: Target Upgrades</b> - Update build dependencies and change TARGET framework to net8.0.",
                "<b>Phase 3: Package Refactoring</b> - Upgrade legacy assemblies and NuGet dependencies.",
                "<b>Phase 4: API Remappings</b> - Code refactoring of WebForms/WCF bindings to Minimal APIs and gRPC."
            ]
            for pt in roadmap_points:
                story.append(Paragraph(f"• {pt}", body_style))
            story.append(Spacer(1, 15))

            # 4. Risk Assessments & Blockers
            story.append(Paragraph("3. Risk Blocker Summary", h2_style))
            if not risk_report.findings:
                story.append(Paragraph("No severe legacy blocker patterns identified in this project.", body_style))
            else:
                for finding in risk_report.findings:
                    story.append(Paragraph(f"• <b>[{finding.impact}] {finding.indicator}</b>", h3_style))
                    story.append(Paragraph(f"<b>Remediation:</b> {finding.remediation}", body_style))
                    story.append(Spacer(1, 5))

            story.append(PageBreak())

            # 5. File by File analysis
            story.append(Paragraph("4. File-by-File AI Suggestions", h2_style))
            for file_path, sug in suggestions.suggestions.items():
                story.append(Paragraph(f"File: {file_path}", h3_style))
                story.append(Paragraph(f"<b>Summary:</b> {sug.summary}", body_style))
                story.append(Paragraph(f"<b>Strategy:</b> {sug.migration_strategy}", body_style))
                
                # Render equivalent preview if not too large
                code_snippet = sug.dotnet8_equivalent.strip()
                if len(code_snippet) > 800:
                    code_snippet = code_snippet[:800] + "\n//... [code truncated for length in PDF] ..."
                
                story.append(Paragraph("<b>Migrated Equivalent Preview:</b>", body_style))
                story.append(Paragraph(code_snippet.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>"), code_style))
                story.append(Spacer(1, 10))

            doc.build(story)
            return True
        except Exception as e:
            # Fallback or log error
            print(f"Error creating PDF: {str(e)}")
            return False
