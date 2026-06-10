import os
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    # pyrefly: ignore [missing-import]
    import google.generativeai as genai
except ImportError:
    genai = None
from src.scanner.models import ProjectAnalysis, AnalyzedFile
from src.risk_engine.models import MigrationRiskReport
from src.database.db import DatabaseManager
from .models import FileMigrationSuggestion, ProjectMigrationSuggestion

# ─── Migration pattern reference (used in prompts) ──────────────────
MIGRATION_PATTERNS = {
    "WCF": "WCF → ASP.NET Core Minimal APIs or gRPC (CoreWCF for compatibility)",
    "WebForms": "WebForms → Blazor Server/WASM or Razor Pages",
    "Global.asax": "Global.asax → Program.cs with WebApplicationBuilder",
    "System.Web": "System.Web.* → Microsoft.AspNetCore.Http (IHttpContextAccessor via DI)",
    "HttpContext.Current": "HttpContext.Current → constructor-injected IHttpContextAccessor",
    "Web.config": "Web.config → appsettings.json + Program.cs configuration",
    "Session": "Session state → IDistributedCache or cookie-based state",
    "ViewState": "ViewState → Blazor component state or React/Vue SPA state",
    "ConfigurationManager": "ConfigurationManager → IConfiguration via DI",
    "SqlConnection": "Raw ADO.NET → Entity Framework Core with DbContext",
    "HttpApplication": "HttpApplication lifecycle → ASP.NET Core middleware pipeline",
}


_SENTINEL = object()


class GeminiClient:
    def __init__(self, db_manager: DatabaseManager, api_key: Optional[str] = _SENTINEL):
        self.db_manager = db_manager
        if api_key is _SENTINEL:
            self.api_key = os.environ.get("GEMINI_API_KEY")
        else:
            self.api_key = api_key
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

        if self.api_key and genai:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None
            self.db_manager.log_message(
                "WARNING",
                "GEMINI_API_KEY not set or google-generativeai not installed. Running in offline/mock mode."
            )

    def _create_suggestion(self, file_path: str, parsed_json: Dict[str, Any]) -> FileMigrationSuggestion:
        """Create FileMigrationSuggestion from parsed JSON with type normalization."""
        # Normalize migration_strategy to string
        strategy = parsed_json.get("migration_strategy")
        if isinstance(strategy, list):
            strategy_str = "\n".join(str(s) for s in strategy)
        elif strategy is not None:
            strategy_str = str(strategy)
        else:
            strategy_str = ""

        # Normalize summary to string
        summary = parsed_json.get("summary", "")
        summary_str = str(summary) if summary is not None else ""

        # Normalize unsupported_apis to list
        unsupported = parsed_json.get("unsupported_apis")
        if isinstance(unsupported, str):
            unsupported_list = [unsupported]
        elif isinstance(unsupported, list):
            unsupported_list = [str(x) for x in unsupported]
        else:
            unsupported_list = []

        # Normalize confidence_score to float
        conf = parsed_json.get("confidence_score")
        try:
            confidence = float(conf) if conf is not None else 0.0
        except (ValueError, TypeError):
            confidence = 0.0

        return FileMigrationSuggestion(
            file_path=file_path,
            summary=summary_str,
            migration_strategy=strategy_str,
            unsupported_apis=unsupported_list,
            dotnet8_equivalent=str(parsed_json.get("dotnet8_equivalent", "")),
            code_diff_markdown=str(parsed_json.get("code_diff_markdown", "")),
            confidence_score=confidence,
        )

    def _compute_hash(self, file_path: str, content: str, technology: str, findings: List[str], prompt: str) -> str:
        """Compute SHA-256 hash of inputs to use as cache key."""
        hash_payload = f"{file_path}\n{content}\n{technology}\n{','.join(findings)}\n{prompt}"
        return hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    def get_migration_suggestion(
        self,
        file_path: str,
        content: str,
        technology: str,
        findings: List[str],
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> FileMigrationSuggestion:
        """Get migration suggestion for a single file, with caching and retry logic."""
        # ── Build prompt first to include in cache key (bust cache on prompt changes) ──
        prompt = self._build_prompt(file_path, content, technology, findings)
        file_hash = self._compute_hash(file_path, content, technology, findings, prompt)

        # ── Check cache ──────────────────────────────────────────
        cached_val = self.db_manager.get_cached_ai_response(file_hash)
        if cached_val:
            try:
                data = json.loads(cached_val)
                self.db_manager.log_message("INFO", f"Cache hit for file: {file_path}")
                return self._create_suggestion(file_path, data)
            except Exception as e:
                self.db_manager.log_message("WARNING", f"Failed to parse cached response for {file_path}: {e}")

        # ── Mock mode ────────────────────────────────────────────
        if not self.model:
            return self._generate_mock_suggestion(file_path, content, technology, findings)

        # ── Call Gemini with exponential backoff ──────────────────
        last_exception = None
        for attempt in range(max_retries):
            try:
                self.db_manager.log_message(
                    "INFO", f"Calling Gemini API for {file_path} (attempt {attempt + 1}/{max_retries})"
                )

                schema = {
                    "type": "OBJECT",
                    "properties": {
                        "summary": {"type": "STRING"},
                        "migration_strategy": {"type": "STRING"},
                        "unsupported_apis": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "dotnet8_equivalent": {"type": "STRING"},
                        "code_diff_markdown": {"type": "STRING"},
                        "confidence_score": {"type": "NUMBER"}
                    },
                    "required": ["summary", "migration_strategy", "unsupported_apis", "dotnet8_equivalent", "code_diff_markdown", "confidence_score"]
                }

                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": schema
                    },
                )

                response_text = response.text.strip()
                parsed_json = json.loads(response_text)

                # Cache response
                self.db_manager.cache_ai_response(file_hash, prompt, response_text)

                return self._create_suggestion(file_path, parsed_json)
            except Exception as e:
                last_exception = e
                self.db_manager.log_message("WARNING", f"Gemini API attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor ** attempt
                    if "429" in str(e) or "quota" in str(e).lower() or "resourceexhausted" in type(e).__name__.lower():
                        sleep_time = 35
                        self.db_manager.log_message("INFO", f"Rate limit (429) hit. Sleeping {sleep_time} seconds to clear the rate limit window...")
                    time.sleep(sleep_time)

        # ── All retries exhausted ────────────────────────────────
        self.db_manager.log_message("ERROR", f"All Gemini retries failed for {file_path}: {last_exception}")
        return FileMigrationSuggestion(
            file_path=file_path,
            summary=f"Failed to generate suggestion: {last_exception}",
            migration_strategy="API Error — check network and GEMINI_API_KEY.",
            unsupported_apis=findings,
            confidence_score=0.0,
        )

    def analyze_project(
        self,
        project_dir: str,
        analysis: ProjectAnalysis,
        risk_report: MigrationRiskReport,
        max_workers: int = 4,
    ) -> ProjectMigrationSuggestion:
        """Process all relevant legacy files in parallel batches."""
        project_suggestion = ProjectMigrationSuggestion()

        # Filter to files worth migrating
        relevant_files: List[AnalyzedFile] = []
        for file in analysis.files:
            has_patterns = len(file.detected_patterns) > 0
            is_legacy_ext = file.extension in {".aspx", ".svc", ".asmx", ".asax"}
            if has_patterns or is_legacy_ext:
                relevant_files.append(file)

        if not relevant_files:
            return project_suggestion

        # Build task list
        tasks = []
        for file in relevant_files:
            file_findings = []
            for finding in risk_report.findings:
                if file.file_path in finding.files:
                    file_findings.append(f"{finding.indicator}: {finding.remediation}")

            tech = self._classify_technology(file)

            full_path = os.path.join(project_dir, file.file_path)
            content = ""
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(full_path, "r", encoding="latin-1") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading file: {e}"

            tasks.append((file.file_path, content, tech, file_findings))

        # Run concurrently
        self.db_manager.log_message("INFO", f"Batch processing {len(tasks)} files with {max_workers} threads.")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.get_migration_suggestion, path, content, tech, findings): path
                for path, content, tech, findings in tasks
            }

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    suggestion = future.result()
                    project_suggestion.suggestions[file_path] = suggestion
                except Exception as exc:
                    self.db_manager.log_message("ERROR", f"Thread execution failed for {file_path}: {exc}")
                    project_suggestion.suggestions[file_path] = FileMigrationSuggestion(
                        file_path=file_path,
                        summary=f"Analysis crashed: {exc}",
                        migration_strategy="Failed to process file.",
                        confidence_score=0.0,
                    )

        self.db_manager.log_message("INFO", "Batch processing finished.")
        return project_suggestion

    @staticmethod
    def _classify_technology(file: AnalyzedFile) -> str:
        """Map file extension/patterns to a descriptive technology label."""
        if file.extension == ".svc" or any("WCF" in p for p in file.detected_patterns):
            return "WCF (Windows Communication Foundation)"
        elif file.extension in {".aspx", ".asmx"} or any("WebForms" in p for p in file.detected_patterns):
            return "ASP.NET WebForms"
        elif file.extension == ".asax":
            return "ASP.NET Global Application (Global.asax)"
        elif any("System.Web" in p or "HttpContext" in p for p in file.detected_patterns):
            return "ASP.NET MVC / Web API (System.Web)"
        elif file.extension == ".config":
            return "XML Configuration (Web.config / App.config)"
        elif file.extension == ".csproj":
            return "MSBuild Project File (.csproj)"
        return "Legacy .NET Component"

    def _build_prompt(self, file_path: str, content: str, technology: str, findings: List[str]) -> str:
        """Build a detailed, structured prompt for Gemini with expert context."""
        findings_str = "\n".join(f"  - {f}" for f in findings) if findings else "  - None identified"

        # Gather relevant migration patterns
        relevant_patterns = []
        for key, pattern in MIGRATION_PATTERNS.items():
            if key.lower() in content.lower() or key.lower() in technology.lower():
                relevant_patterns.append(f"  • {pattern}")
        patterns_str = "\n".join(relevant_patterns) if relevant_patterns else "  • General .NET Framework to .NET 8 upgrade"

        # Truncate very large files to avoid token limits
        max_content_len = 12000
        truncated = False
        if len(content) > max_content_len:
            content = content[:max_content_len]
            truncated = True

        return f"""You are a Principal .NET Architect with 15+ years of experience specializing in enterprise .NET Framework to .NET 8 migrations. You have deep expertise in WCF, WebForms, ASP.NET MVC, and modern .NET 8 patterns including Minimal APIs, Blazor, and middleware pipelines.

## Task
Analyze the following legacy .NET Framework source file and generate a precise, production-quality migration plan to port it to .NET 8.

## Source File Information
- **File Path**: `{file_path}`
- **Detected Technology**: {technology}
- **Risk Findings**:
{findings_str}

## Applicable Migration Patterns
{patterns_str}

## Source Code
```
{content}
```
{"[NOTE: File was truncated to fit context window. Focus on the visible patterns.]" if truncated else ""}

## Instructions
1. Analyze every legacy API usage, pattern, and dependency in this file.
2. Provide a complete, compilable .NET 8 equivalent — not a stub or skeleton. The C# code MUST be beautifully formatted, using proper multiline structure (with actual newline characters \\n) and standard indentation (4 spaces). Do NOT output it as a single-line string.
3. Preserve ALL business logic, validation rules, and data access patterns.
4. Use modern .NET 8 best practices: dependency injection, middleware, minimal APIs or controller-based APIs, EF Core where applicable.
5. Add XML documentation comments on public members in the migrated code.
6. Generate a meaningful git-style diff showing the conceptual transformation. The diff MUST be properly structured with actual newline characters \\n for readability.

## Response Schema
Return a JSON object with exactly these fields:
{{
  "summary": "2-3 sentence description of the file's purpose and which legacy APIs it uses.",
  "migration_strategy": "Step-by-step migration roadmap (numbered steps). Be specific about which APIs to replace and with what.",
  "unsupported_apis": ["List every specific legacy class/method/namespace that must be replaced, e.g. 'System.Web.HttpContext.Current', 'System.ServiceModel.ServiceContractAttribute'"],
  "dotnet8_equivalent": "The complete, compilable .NET 8 C# code that replaces this file, formatted with proper indentation and newline characters (\\n). Make sure it looks like standard multiline C# source code.",
  "code_diff_markdown": "A conceptual git-style diff showing key lines removed (-) and added (+), formatted with proper indentation and newline characters (\\n).",
  "confidence_score": 0.85
}}

## Confidence Score Calibration
- **0.90-1.00**: Direct 1:1 API mapping exists (e.g., ConfigurationManager → IConfiguration)
- **0.70-0.89**: Clear migration path but requires structural changes (e.g., WCF → Minimal API)
- **0.50-0.69**: Significant rewrite needed, multiple architectural decisions required
- **0.30-0.49**: Partial migration possible, some features may need alternative approaches
- **0.00-0.29**: No clear migration path, requires complete redesign

Return ONLY the JSON object. Do not wrap in markdown code fences."""

    def _generate_mock_suggestion(
        self, file_path: str, content: str, technology: str, findings: List[str]
    ) -> FileMigrationSuggestion:
        """Generate high-quality offline mock suggestions when API key is missing."""
        _, ext = os.path.splitext(file_path.lower())
        basename = os.path.basename(file_path)

        if ext == ".svc" and ext != ".cs":
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"WCF service host file '{basename}' that routes SOAP requests to the service implementation. This file defines the ServiceHost directive used by IIS to activate the WCF service.",
                migration_strategy=(
                    "1. Remove the .svc file entirely — .NET 8 does not use .svc hosting.\n"
                    "2. Register the service as a Minimal API endpoint in Program.cs.\n"
                    "3. If SOAP compatibility is required, use CoreWCF NuGet package.\n"
                    "4. For new clients, prefer gRPC with Protobuf contracts."
                ),
                unsupported_apis=["System.ServiceModel.Activation.ServiceHostFactory", "<%@ ServiceHost %> directive"],
                dotnet8_equivalent=self._mock_svc_migration(basename),
                code_diff_markdown=(
                    "- <%@ ServiceHost Language=\"C#\" Service=\"LegacyApp.Services.OrderService\" %>\n"
                    "+ // Service registered in Program.cs:\n"
                    "+ app.MapGroup(\"/api/orders\").MapOrderEndpoints();"
                ),
                confidence_score=0.8,
            )

        elif ext == ".cs" and any(k in content for k in ["ServiceContract", "OperationContract"]):
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"WCF service implementation '{basename}' with [ServiceContract] and [OperationContract] attributes, using ADO.NET for data access via SqlConnection and ConfigurationManager.",
                migration_strategy=(
                    "1. Replace [ServiceContract] interface with ASP.NET Core Minimal API endpoint group.\n"
                    "2. Replace [OperationContract] methods with MapGet/MapPost/MapPut/MapDelete handlers.\n"
                    "3. Replace [DataContract]/[DataMember] DTOs with C# records.\n"
                    "4. Replace ConfigurationManager with IConfiguration via dependency injection.\n"
                    "5. Replace raw SqlConnection/SqlCommand with Entity Framework Core DbContext.\n"
                    "6. Add proper input validation with FluentValidation or Data Annotations."
                ),
                unsupported_apis=[
                    "System.ServiceModel.ServiceContractAttribute",
                    "System.ServiceModel.OperationContractAttribute",
                    "System.ServiceModel.Activation.AspNetCompatibilityRequirementsAttribute",
                    "System.Runtime.Serialization.DataContractAttribute",
                    "System.Configuration.ConfigurationManager",
                ],
                dotnet8_equivalent=self._mock_wcf_cs_migration(basename),
                code_diff_markdown=(
                    "- [ServiceContract]\n"
                    "- public interface IOrderService { ... }\n"
                    "- [AspNetCompatibilityRequirements(...)]\n"
                    "- public class OrderService : IOrderService { ... }\n"
                    "+ public static class OrderEndpoints\n"
                    "+ {\n"
                    "+     public static RouteGroupBuilder MapOrderEndpoints(this RouteGroupBuilder group)\n"
                    "+     {\n"
                    "+         group.MapGet(\"/\", async (AppDbContext db) => await db.Orders.ToListAsync());\n"
                    "+         group.MapGet(\"/{id}\", async (int id, AppDbContext db) => ...);\n"
                    "+         group.MapPost(\"/\", async (CreateOrderRequest req, AppDbContext db) => ...);\n"
                    "+         return group;\n"
                    "+     }\n"
                    "+ }"
                ),
                confidence_score=0.78,
            )

        elif ext in {".aspx"}:
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"WebForms page '{basename}' using server controls (GridView, UpdatePanel, ScriptManager), ViewState for state management, and ASPX markup with code-behind pattern.",
                migration_strategy=(
                    "1. Replace .aspx markup with a Blazor component (.razor) or Razor Page.\n"
                    "2. Replace <asp:GridView> with a Blazor table component or MudBlazor DataGrid.\n"
                    "3. Replace <asp:UpdatePanel> with Blazor's built-in re-rendering.\n"
                    "4. Remove ViewState — use Blazor component state (@code { }) instead.\n"
                    "5. Replace code-behind event handlers (Page_Load, Button_Click) with Blazor lifecycle methods."
                ),
                unsupported_apis=[
                    "System.Web.UI.Page", "asp:GridView", "asp:UpdatePanel",
                    "asp:ScriptManager", "ViewState", "runat=\"server\"",
                ],
                dotnet8_equivalent=self._mock_aspx_migration(basename),
                code_diff_markdown=(
                    "- <%@ Page Language=\"C#\" Inherits=\"LegacyApp.Default\" %>\n"
                    "- <asp:GridView ID=\"OrdersGrid\" runat=\"server\" ... />\n"
                    "- <asp:UpdatePanel ID=\"UpdatePanel1\" runat=\"server\">\n"
                    "+ @page \"/\"\n"
                    "+ @inject IOrderService OrderService\n"
                    "+ <MudTable Items=\"@orders\" Hover=\"true\" Striped=\"true\">\n"
                    "+     <HeaderContent>...</HeaderContent>\n"
                    "+     <RowTemplate>...</RowTemplate>\n"
                    "+ </MudTable>"
                ),
                confidence_score=0.72,
            )

        elif ext == ".cs" and any(k in content for k in ["Page_Load", "System.Web.UI.Page", "ViewState"]):
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"WebForms code-behind '{basename}' with Page_Load lifecycle, ViewState usage, Session state, HttpContext.Current access, and direct ADO.NET database operations.",
                migration_strategy=(
                    "1. Convert Page class to a Blazor component @code block.\n"
                    "2. Replace Page_Load with OnInitializedAsync().\n"
                    "3. Replace ViewState with component-level fields/properties.\n"
                    "4. Replace Session access with IDistributedCache or cascading parameters.\n"
                    "5. Replace HttpContext.Current with injected IHttpContextAccessor.\n"
                    "6. Replace SqlConnection/SqlCommand with EF Core DbContext."
                ),
                unsupported_apis=[
                    "System.Web.UI.Page", "Page_Load", "ViewState",
                    "HttpContext.Current", "Session[]", "Response.Redirect",
                    "ConfigurationManager.ConnectionStrings",
                ],
                dotnet8_equivalent=self._mock_codebehind_migration(basename),
                code_diff_markdown=(
                    "- public partial class Default : System.Web.UI.Page\n"
                    "- {\n"
                    "-     protected void Page_Load(object sender, EventArgs e) { ... }\n"
                    "-     ViewState[\"CurrentUser\"] = HttpContext.Current.User.Identity.Name;\n"
                    "- }\n"
                    "+ @page \"/\"\n"
                    "+ @inject IHttpContextAccessor HttpContextAccessor\n"
                    "+ @inject AppDbContext Db\n"
                    "+ @code {\n"
                    "+     private List<OrderDto> orders = new();\n"
                    "+     protected override async Task OnInitializedAsync()\n"
                    "+     {\n"
                    "+         orders = await Db.Orders.Include(o => o.Customer).ToListAsync();\n"
                    "+     }\n"
                    "+ }"
                ),
                confidence_score=0.74,
            )

        elif ext == ".cs" and "asax" in file_path.lower():
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"ASP.NET Global Application file '{basename}' implementing HttpApplication lifecycle events (Application_Start, Application_BeginRequest, Application_Error, Session_Start).",
                migration_strategy=(
                    "1. Move Application_Start logic to Program.cs builder configuration.\n"
                    "2. Replace Application_BeginRequest/EndRequest with ASP.NET Core middleware.\n"
                    "3. Replace Application_Error with app.UseExceptionHandler() middleware.\n"
                    "4. Replace Session_Start with session configuration in Program.cs.\n"
                    "5. Replace Application/Session state with DI-registered singleton/scoped services."
                ),
                unsupported_apis=[
                    "System.Web.HttpApplication", "Application_Start", "Application_BeginRequest",
                    "Application_Error", "Session_Start", "HttpContext.Current",
                ],
                dotnet8_equivalent=self._mock_global_asax_migration(),
                code_diff_markdown=(
                    "- public class MvcApplication : System.Web.HttpApplication\n"
                    "- {\n"
                    "-     protected void Application_Start() { ... }\n"
                    "-     protected void Application_BeginRequest() { ... }\n"
                    "- }\n"
                    "+ var builder = WebApplication.CreateBuilder(args);\n"
                    "+ builder.Services.AddControllersWithViews();\n"
                    "+ var app = builder.Build();\n"
                    "+ app.UseMiddleware<RequestTimingMiddleware>();\n"
                    "+ app.UseExceptionHandler(\"/Error\");\n"
                    "+ app.Run();"
                ),
                confidence_score=0.90,
            )

        elif ext == ".cs" and any(k in content for k in ["HttpContext.Current", "HttpApplication", "System.Web.Mvc"]):
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"Legacy ASP.NET MVC controller or HTTP module '{basename}' using HttpContext.Current, Session, Application state, Cache API, and ConfigurationManager.",
                migration_strategy=(
                    "1. Replace HttpContext.Current with constructor-injected IHttpContextAccessor.\n"
                    "2. Replace System.Web.Mvc.Controller with Microsoft.AspNetCore.Mvc.Controller.\n"
                    "3. Replace ConfigurationManager with IConfiguration.\n"
                    "4. Replace ASP.NET Cache with IMemoryCache or IDistributedCache.\n"
                    "5. Replace Session direct access with HttpContext.Session extension methods.\n"
                    "6. Replace Application state with a singleton service registered in DI."
                ),
                unsupported_apis=[
                    "HttpContext.Current", "System.Web.Mvc.Controller",
                    "HttpContext.Current.Cache", "HttpContext.Current.Application",
                    "HttpContext.Current.Server.MapPath", "ConfigurationManager",
                ],
                dotnet8_equivalent=self._mock_controller_migration(basename),
                code_diff_markdown=(
                    "- using System.Web;\n"
                    "- using System.Web.Mvc;\n"
                    "- var userName = HttpContext.Current.User.Identity.Name;\n"
                    "- HttpContext.Current.Cache[\"key\"] = value;\n"
                    "+ using Microsoft.AspNetCore.Mvc;\n"
                    "+ using Microsoft.Extensions.Caching.Memory;\n"
                    "+ public HomeController(IHttpContextAccessor ctx, IMemoryCache cache, IConfiguration config)\n"
                    "+ var userName = _httpContextAccessor.HttpContext?.User?.Identity?.Name;"
                ),
                confidence_score=0.85,
            )

        elif ext == ".config":
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"XML configuration file '{basename}' containing connection strings, system.web settings, system.serviceModel WCF bindings, Entity Framework configuration, and custom HTTP modules.",
                migration_strategy=(
                    "1. Move <connectionStrings> to appsettings.json under \"ConnectionStrings\" key.\n"
                    "2. Move <appSettings> to appsettings.json.\n"
                    "3. Replace <system.web> authentication/authorization with ASP.NET Core Identity middleware.\n"
                    "4. Replace <system.serviceModel> WCF config with code-based endpoint registration.\n"
                    "5. Replace <entityFramework> config with EF Core registration in Program.cs.\n"
                    "6. Replace <httpModules> with ASP.NET Core middleware in Program.cs."
                ),
                unsupported_apis=[
                    "<system.web>", "<system.serviceModel>", "<httpModules>",
                    "ConfigurationManager", "Forms authentication mode",
                ],
                dotnet8_equivalent=self._mock_config_migration(),
                code_diff_markdown=(
                    '- <connectionStrings>\n'
                    '-   <add name="DefaultConnection" connectionString="..." />\n'
                    '- </connectionStrings>\n'
                    '- <system.web>\n'
                    '-   <authentication mode="Forms" />\n'
                    '- </system.web>\n'
                    '+ // appsettings.json:\n'
                    '+ "ConnectionStrings": { "DefaultConnection": "..." },\n'
                    '+ // Program.cs:\n'
                    '+ builder.Services.AddAuthentication().AddCookie();'
                ),
                confidence_score=0.88,
            )

        else:
            return FileMigrationSuggestion(
                file_path=file_path,
                summary=f"Legacy .NET component '{basename}' requiring upgrade to .NET 8.",
                migration_strategy=(
                    "1. Update target framework to net8.0 in .csproj.\n"
                    "2. Replace legacy assembly references with modern NuGet packages.\n"
                    "3. Update namespace imports for .NET 8 compatibility."
                ),
                unsupported_apis=findings,
                dotnet8_equivalent='<Project Sdk="Microsoft.NET.Sdk.Web">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n</Project>',
                code_diff_markdown=(
                    "- <TargetFrameworkVersion>v4.7.2</TargetFrameworkVersion>\n"
                    "+ <TargetFramework>net8.0</TargetFramework>"
                ),
                confidence_score=0.80,
            )

    # ─── Mock code generators ─────────────────────────────────────────

    @staticmethod
    def _mock_svc_migration(basename: str) -> str:
        service_name = basename.replace(".svc", "")
        return f"""// .svc file is eliminated in .NET 8.
// Service is registered in Program.cs as a Minimal API:

// Program.cs
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddDbContext<AppDbContext>(o =>
    o.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

var app = builder.Build();
app.MapGroup("/api/{service_name.lower()}s").Map{service_name}Endpoints();
app.Run();"""

    @staticmethod
    def _mock_wcf_cs_migration(basename: str) -> str:
        return """using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;

namespace LegacyApp.Endpoints;

/// <summary>Order data transfer object.</summary>
public record OrderDto(int OrderId, string CustomerName, DateTime OrderDate, decimal TotalAmount, string Status);

/// <summary>Request payload for creating a new order.</summary>
public record CreateOrderRequest(int CustomerId, List<OrderItemRequest> Items);
public record OrderItemRequest(int ProductId, int Quantity, decimal UnitPrice);

/// <summary>Standard API response envelope.</summary>
public record ServiceResponse(bool Success, string Message, int? OrderId = null);

/// <summary>Minimal API endpoints replacing the WCF OrderService.</summary>
public static class OrderEndpoints
{
    public static RouteGroupBuilder MapOrderEndpoints(this RouteGroupBuilder group)
    {
        group.MapGet("/", GetAllOrders).WithName("GetOrders").WithOpenApi();
        group.MapGet("/{id:int}", GetOrderById).WithName("GetOrder").WithOpenApi();
        group.MapPost("/", CreateOrder).WithName("CreateOrder").WithOpenApi();
        group.MapPut("/{id:int}/status", UpdateStatus).WithName("UpdateOrderStatus").WithOpenApi();
        group.MapDelete("/{id:int}", CancelOrder).WithName("CancelOrder").WithOpenApi();
        return group;
    }

    private static async Task<Ok<List<OrderDto>>> GetAllOrders(AppDbContext db)
    {
        var orders = await db.Orders
            .Include(o => o.Customer)
            .OrderByDescending(o => o.OrderDate)
            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
            .ToListAsync();
        return TypedResults.Ok(orders);
    }

    private static async Task<Results<Ok<OrderDto>, NotFound>> GetOrderById(int id, AppDbContext db)
    {
        var order = await db.Orders.Include(o => o.Customer)
            .Where(o => o.OrderId == id)
            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
            .FirstOrDefaultAsync();
        return order is not null ? TypedResults.Ok(order) : TypedResults.NotFound();
    }

    private static async Task<Created<ServiceResponse>> CreateOrder(CreateOrderRequest req, AppDbContext db)
    {
        var total = req.Items.Sum(i => i.Quantity * i.UnitPrice);
        var order = new Order
        {
            CustomerId = req.CustomerId,
            OrderDate = DateTime.UtcNow,
            TotalAmount = total,
            Status = "Pending",
            Items = req.Items.Select(i => new OrderItem
            {
                ProductId = i.ProductId,
                Quantity = i.Quantity,
                UnitPrice = i.UnitPrice
            }).ToList()
        };

        db.Orders.Add(order);
        await db.SaveChangesAsync();

        return TypedResults.Created($"/api/orders/{order.OrderId}",
            new ServiceResponse(true, "Order created.", order.OrderId));
    }

    private static async Task<Results<Ok<ServiceResponse>, NotFound>> UpdateStatus(
        int id, string newStatus, AppDbContext db)
    {
        var order = await db.Orders.FindAsync(id);
        if (order is null) return TypedResults.NotFound();
        order.Status = newStatus;
        await db.SaveChangesAsync();
        return TypedResults.Ok(new ServiceResponse(true, "Status updated."));
    }

    private static async Task<Results<Ok<ServiceResponse>, NotFound>> CancelOrder(int id, AppDbContext db)
    {
        var order = await db.Orders.FindAsync(id);
        if (order is null) return TypedResults.NotFound();
        order.Status = "Cancelled";
        await db.SaveChangesAsync();
        return TypedResults.Ok(new ServiceResponse(true, "Order cancelled."));
    }
}"""

    @staticmethod
    def _mock_aspx_migration(basename: str) -> str:
        return """@page "/"
@using LegacyApp.Data
@inject IOrderService OrderService
@inject IHttpContextAccessor HttpContextAccessor

<PageTitle>Enterprise Dashboard</PageTitle>

<div class="container">
    <h1>Enterprise Dashboard</h1>

    <MudTable Items="@orders" Hover="true" Striped="true" Loading="@isLoading"
              Pagination="new MudTablePager { PageSizeOptions = new[] { 10, 25, 50 } }">
        <HeaderContent>
            <MudTh>Order #</MudTh>
            <MudTh>Customer</MudTh>
            <MudTh>Date</MudTh>
            <MudTh>Total</MudTh>
            <MudTh>Status</MudTh>
            <MudTh>Actions</MudTh>
        </HeaderContent>
        <RowTemplate>
            <MudTd>@context.OrderId</MudTd>
            <MudTd>@context.CustomerName</MudTd>
            <MudTd>@context.OrderDate.ToString("MM/dd/yyyy")</MudTd>
            <MudTd>@context.TotalAmount.ToString("C")</MudTd>
            <MudTd><MudChip Color="@GetStatusColor(context.Status)">@context.Status</MudChip></MudTd>
            <MudTd><MudButton Variant="Variant.Text" OnClick="() => ViewOrder(context.OrderId)">View</MudButton></MudTd>
        </RowTemplate>
    </MudTable>

    <div class="mt-4">
        <MudText Typo="Typo.body1">Total Orders: @totalOrders</MudText>
        <MudText Typo="Typo.body1">Revenue: @totalRevenue.ToString("C")</MudText>
    </div>

    <MudButton Variant="Variant.Filled" Color="Color.Primary" OnClick="RefreshData">Refresh</MudButton>
</div>

@code {
    private List<OrderDto> orders = new();
    private bool isLoading = true;
    private int totalOrders;
    private decimal totalRevenue;

    protected override async Task OnInitializedAsync()
    {
        await RefreshData();
    }

    private async Task RefreshData()
    {
        isLoading = true;
        orders = await OrderService.GetAllOrdersAsync();
        totalOrders = orders.Count;
        totalRevenue = orders.Where(o => o.Status == "Completed").Sum(o => o.TotalAmount);
        isLoading = false;
    }

    private void ViewOrder(int orderId)
    {
        NavigationManager.NavigateTo($"/orders/{orderId}");
    }

    private Color GetStatusColor(string status) => status switch
    {
        "Completed" => Color.Success,
        "Pending" => Color.Warning,
        "Cancelled" => Color.Error,
        _ => Color.Default
    };
}"""

    @staticmethod
    def _mock_codebehind_migration(basename: str) -> str:
        return """@page "/"
@using Microsoft.AspNetCore.Http
@using Microsoft.EntityFrameworkCore
@inject AppDbContext Db
@inject IHttpContextAccessor HttpContextAccessor
@inject NavigationManager NavigationManager

<PageTitle>Dashboard</PageTitle>

@code {
    private List<OrderDto> orders = new();
    private string currentUser = "";
    private int totalOrders;
    private decimal totalRevenue;

    protected override async Task OnInitializedAsync()
    {
        // Replaces HttpContext.Current.User
        currentUser = HttpContextAccessor.HttpContext?.User?.Identity?.Name ?? "Anonymous";

        // Replaces ViewState + Page_Load data binding
        orders = await Db.Orders
            .Include(o => o.Customer)
            .OrderByDescending(o => o.OrderDate)
            .Take(100)
            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
            .ToListAsync();

        var summary = await Db.Orders
            .Where(o => o.OrderDate.Year == DateTime.Now.Year)
            .GroupBy(_ => 1)
            .Select(g => new { Count = g.Count(), Revenue = g.Sum(o => o.TotalAmount) })
            .FirstOrDefaultAsync();

        totalOrders = summary?.Count ?? 0;
        totalRevenue = summary?.Revenue ?? 0;
    }
}"""

    @staticmethod
    def _mock_controller_migration(basename: str) -> str:
        return """using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Configuration;
using Microsoft.EntityFrameworkCore;

namespace LegacyApp.Controllers;

/// <summary>Home controller migrated to ASP.NET Core with dependency injection.</summary>
public class HomeController : Controller
{
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly IMemoryCache _cache;
    private readonly IConfiguration _configuration;
    private readonly AppDbContext _db;

    public HomeController(
        IHttpContextAccessor httpContextAccessor,
        IMemoryCache cache,
        IConfiguration configuration,
        AppDbContext db)
    {
        _httpContextAccessor = httpContextAccessor;
        _cache = cache;
        _configuration = configuration;
        _db = db;
    }

    public async Task<IActionResult> Index()
    {
        // Replaces HttpContext.Current.User.Identity.Name
        var userName = _httpContextAccessor.HttpContext?.User?.Identity?.Name ?? "Anonymous";
        ViewBag.UserName = userName;
        ViewBag.ServerTime = DateTime.UtcNow;

        // Replaces HttpContext.Current.Cache with IMemoryCache
        if (!_cache.TryGetValue("DashboardStats", out Dictionary<string, object>? stats))
        {
            stats = await LoadDashboardStatsAsync();
            _cache.Set("DashboardStats", stats, TimeSpan.FromMinutes(5));
        }
        ViewBag.Stats = stats;

        return View();
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> UpdateProfile(string email, string phone)
    {
        var userId = Request.Cookies["UserId"];
        if (string.IsNullOrEmpty(userId))
            return Unauthorized("Not authenticated");

        var user = await _db.Users.FindAsync(int.Parse(userId));
        if (user is null) return NotFound();

        user.Email = email;
        user.Phone = phone;
        await _db.SaveChangesAsync();

        Response.Cookies.Append("LastUpdate", DateTime.UtcNow.ToString(), new CookieOptions
        {
            Expires = DateTimeOffset.UtcNow.AddDays(30)
        });

        TempData["Message"] = "Profile updated successfully.";
        return RedirectToAction("Index");
    }

    private async Task<Dictionary<string, object>> LoadDashboardStatsAsync()
    {
        var stats = await _db.Orders
            .GroupBy(_ => 1)
            .Select(g => new
            {
                TotalOrders = g.Count(),
                TotalCustomers = g.Select(o => o.CustomerId).Distinct().Count(),
                Revenue = g.Where(o => o.Status == "Completed").Sum(o => o.TotalAmount)
            })
            .FirstOrDefaultAsync();

        return new Dictionary<string, object>
        {
            ["TotalOrders"] = stats?.TotalOrders ?? 0,
            ["TotalCustomers"] = stats?.TotalCustomers ?? 0,
            ["Revenue"] = stats?.Revenue ?? 0m
        };
    }
}"""

    @staticmethod
    def _mock_config_migration() -> str:
        return """{
  "ConnectionStrings": {
    "DefaultConnection": "Server=.\\\\SQLEXPRESS;Database=LegacyAppDB;Trusted_Connection=true;TrustServerCertificate=true",
    "ReportingDB": "Server=.\\\\SQLEXPRESS;Database=ReportingDB;Trusted_Connection=true;TrustServerCertificate=true"
  },
  "AppSettings": {
    "MaxPageSize": 100,
    "EnableAuditLog": true,
    "SmtpServer": "smtp.company.internal"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  }
}

// Program.cs — replaces Web.config system sections:
// var builder = WebApplication.CreateBuilder(args);
//
// // Replaces <system.web><authentication mode="Forms">
// builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
//     .AddCookie(options => { options.LoginPath = "/login"; options.ExpireTimeSpan = TimeSpan.FromDays(2); });
//
// // Replaces <system.web><sessionState>
// builder.Services.AddDistributedMemoryCache();
// builder.Services.AddSession(options => { options.IdleTimeout = TimeSpan.FromMinutes(20); });
//
// // Replaces <entityFramework>
// builder.Services.AddDbContext<AppDbContext>(o =>
//     o.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
//
// // Replaces <httpModules><add name="AuditModule">
// app.UseMiddleware<AuditMiddleware>();"""

    @staticmethod
    def _mock_global_asax_migration() -> str:
        return """// Program.cs — replaces Global.asax.cs entirely

using LegacyApp.Middleware;

var builder = WebApplication.CreateBuilder(args);

// Service registration (replaces Application_Start)
builder.Services.AddControllersWithViews();
builder.Services.AddDbContext<AppDbContext>(o =>
    o.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
builder.Services.AddMemoryCache();
builder.Services.AddSession(o => o.IdleTimeout = TimeSpan.FromMinutes(20));
builder.Services.AddSingleton<IAppMetrics, AppMetrics>();

var app = builder.Build();

// Middleware pipeline (replaces Application_BeginRequest/EndRequest)
app.UseMiddleware<RequestTimingMiddleware>();
app.UseExceptionHandler("/Error");
app.UseHsts();
app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.UseSession();
app.MapControllerRoute("default", "{controller=Home}/{action=Index}/{id?}");

app.Run();

// RequestTimingMiddleware.cs — replaces Application_BeginRequest/EndRequest
namespace LegacyApp.Middleware;

/// <summary>Middleware that logs slow requests (replaces HttpApplication events).</summary>
public class RequestTimingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RequestTimingMiddleware> _logger;

    public RequestTimingMiddleware(RequestDelegate next, ILogger<RequestTimingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, IAppMetrics metrics)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        metrics.IncrementRequestCount();

        await _next(context);

        stopwatch.Stop();
        if (stopwatch.ElapsedMilliseconds > 500)
        {
            _logger.LogWarning("[SLOW REQUEST] {Path} took {Elapsed}ms",
                context.Request.Path, stopwatch.ElapsedMilliseconds);
        }
    }
}"""
