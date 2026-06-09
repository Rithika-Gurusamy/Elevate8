import os
from typing import List, Dict, Any, Set
from src.scanner.models import ProjectAnalysis, AnalyzedFile
from .models import MigrationRiskReport, RiskFinding

class RiskEngine:
    LEGACY_PACKAGES = {
        "entityframework",
        "log4net",
        "nlog",
        "ajaxcontroltoolkit",
        "microsoft.aspnet.webapi",
        "microsoft.aspnet.mvc",
        "microsoft.aspnet.razor",
        "microsoft.aspnet.webpages",
        "microsoft.aspnet.web.optimization",
        "enterpriselibrary.common",
        "autofac.mvc5"
    }

    def evaluate_project(self, analysis: ProjectAnalysis) -> MigrationRiskReport:
        """Evaluate project analysis and generate a risk report."""
        # 1. WCF Score component
        wcf_files = []
        wcf_patterns_count = 0
        for f in analysis.files:
            if f.extension == '.svc' or any('WCF' in p for p in f.detected_patterns):
                wcf_files.append(f.file_path)
                wcf_patterns_count += len([p for p in f.detected_patterns if 'WCF' in p])
                if f.extension == '.svc':
                    wcf_patterns_count += 1
        
        wcf_ratio = min(1.0, wcf_patterns_count / 5.0) if wcf_patterns_count > 0 else 0.0
        wcf_component_score = wcf_ratio * 30

        # 2. WebForms Score component
        webforms_files = []
        webforms_patterns_count = 0
        for f in analysis.files:
            is_wf_file = f.extension in {'.aspx', '.asmx', '.asax'}
            has_wf_pattern = any('WebForms' in p or 'ASPX' in p or 'ASMX' in p for p in f.detected_patterns)
            if is_wf_file or has_wf_pattern:
                webforms_files.append(f.file_path)
                webforms_patterns_count += len([p for p in f.detected_patterns if 'WebForms' in p or 'ASPX' in p or 'ASMX' in p])
                if is_wf_file:
                    webforms_patterns_count += 1
                    
        webforms_ratio = min(1.0, webforms_patterns_count / 10.0) if webforms_patterns_count > 0 else 0.0
        webforms_component_score = webforms_ratio * 30

        # 3. System.Web Score component
        system_web_files = []
        system_web_patterns_count = 0
        for f in analysis.files:
            has_sw_pattern = any('System.Web' in p or 'HttpContext' in p for p in f.detected_patterns)
            if has_sw_pattern:
                system_web_files.append(f.file_path)
                system_web_patterns_count += len([p for p in f.detected_patterns if 'System.Web' in p or 'HttpContext' in p])
                
        system_web_ratio = min(1.0, system_web_patterns_count / 10.0) if system_web_patterns_count > 0 else 0.0
        system_web_component_score = system_web_ratio * 20

        # 4. Legacy Packages component
        detected_legacy_packages = []
        for dep in analysis.dependencies.keys():
            dep_lower = dep.lower()
            # Direct matches or prefix matches for legacy ASP.NET / System.Web NuGet packages
            is_legacy = (
                dep_lower in self.LEGACY_PACKAGES or
                dep_lower.startswith("microsoft.aspnet.") or
                dep_lower.startswith("system.web.")
            )
            if is_legacy:
                detected_legacy_packages.append(dep)

        legacy_ratio = min(1.0, len(detected_legacy_packages) / 4.0) if detected_legacy_packages else 0.0
        legacy_component_score = legacy_ratio * 10

        # 5. Config Complexity component
        config_files = [f.file_path for f in analysis.files if f.extension == '.config']
        config_points = len(config_files) * 2
        
        has_web_config_legacy = 'Legacy <system.web> Configuration' in analysis.detected_patterns
        has_wcf_config_legacy = 'WCF <system.serviceModel> Configuration' in analysis.detected_patterns

        if has_web_config_legacy:
            config_points += 3
        if has_wcf_config_legacy:
            config_points += 5

        config_ratio = min(1.0, config_points / 10.0) if config_points > 0 else 0.0
        config_component_score = config_ratio * 10

        # Sum components
        risk_score = round(
            wcf_component_score +
            webforms_component_score +
            system_web_component_score +
            legacy_component_score +
            config_component_score
        )

        # Risk categories
        if risk_score <= 30:
            category = "Low"
        elif risk_score <= 60:
            category = "Medium"
        elif risk_score <= 80:
            category = "High"
        else:
            category = "Critical"

        # Generate findings
        findings = []
        if wcf_patterns_count > 0:
            findings.append(RiskFinding(
                indicator="WCF",
                impact="High",
                count=wcf_patterns_count,
                files=wcf_files,
                remediation="WCF is not natively supported in .NET 8. Migrate services to gRPC, CoreWCF, or ASP.NET Core Minimal APIs."
            ))

        if webforms_patterns_count > 0:
            findings.append(RiskFinding(
                indicator="WebForms",
                impact="Critical",
                count=webforms_patterns_count,
                files=webforms_files,
                remediation="ASP.NET WebForms is not supported in .NET 8. Rewrite interface components using ASP.NET Core Razor Pages, Blazor, or a modern SPA framework (React/Vue) with Web API."
            ))

        if system_web_patterns_count > 0:
            findings.append(RiskFinding(
                indicator="System.Web",
                impact="Medium",
                count=system_web_patterns_count,
                files=system_web_files,
                remediation="System.Web is deprecated. Replace HttpContext.Current usage with dependency injection of IHttpContextAccessor. Migrate handlers/modules to ASP.NET Core Middleware."
            ))

        if detected_legacy_packages:
            findings.append(RiskFinding(
                indicator="Legacy Packages",
                impact="Medium",
                count=len(detected_legacy_packages),
                files=[f.file_path for f in analysis.files if f.extension == '.csproj' or 'packages.config' in f.file_path],
                remediation=f"Upgrade legacy NuGet packages to modern versions targeting .NET 8. Legacy packages found: {', '.join(detected_legacy_packages)}"
            ))

        if config_points > 0:
            config_desc = f"Detected {len(config_files)} configuration file(s)"
            if has_web_config_legacy or has_wcf_config_legacy:
                details = []
                if has_web_config_legacy: details.append("system.web")
                if has_wcf_config_legacy: details.append("system.serviceModel")
                config_desc += f" containing legacy configuration elements: <{', '.join(details)}>"
            findings.append(RiskFinding(
                indicator="Config Complexity",
                impact="Low",
                count=len(config_files),
                files=config_files,
                remediation="Convert XML configurations (Web.config/App.config) to JSON-based appsettings.json. Migrate WCF endpoint configurations to code-based initialization."
            ))

        # Config complexity details
        config_details = {
            "config_files_count": len(config_files),
            "has_system_web_config": has_web_config_legacy,
            "has_wcf_config": has_wcf_config_legacy,
            "config_points": config_points
        }

        # Unsupported APIs
        unsupported_apis = []
        if system_web_patterns_count > 0:
            unsupported_apis.append("HttpContext.Current")
            unsupported_apis.append("System.Web.* namespaces")
        if wcf_patterns_count > 0:
            unsupported_apis.append("System.ServiceModel.* namespaces")

        return MigrationRiskReport(
            risk_score=risk_score,
            risk_category=category,
            findings=findings,
            legacy_packages=detected_legacy_packages,
            unsupported_apis=unsupported_apis,
            config_complexity_details=config_details
        )
