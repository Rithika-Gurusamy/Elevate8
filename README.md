# ⚡ Elevate8 — Enterprise .NET Framework to .NET 8 AI Migration Assistant

This is an automated migration utility designed to accelerate the transition of legacy .NET Framework applications (specifically WCF, ASP.NET WebForms, and legacy System.Web MVC components) to modern, cross-platform, high-performance .NET 8.0.

By combining static analysis, automated risk assessment scoring, context-enriched Gemini AI translation, and an interactive side-by-side diff dashboard, Elevate8 mitigates the risks, efforts, and regressions commonly associated with legacy codebase upgrades.

---

Demo video link : https://www.loom.com/share/cbeb720fe3814e849aae0861ce984647

## 💻 Getting Started & Quick Start

### 1. Installation
Clone the repository and set up a virtual python environment:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY="your-google-gemini-api-key"
GEMINI_MODEL="gemini-2.5-flash"
```
*Note: If `GEMINI_API_KEY` is not provided, the application runs in offline/mock mode using high-fidelity local blueprint templates.*

---

## 🛠️ Usage & CLI Reference

### A. Run Directory or File Analysis
To scan, assess, and automatically generate migrations for a project directory:
```powershell
python Project/src/cli/main.py analyze Project/input_dotnet_legacy_code
```

#### ⚡ Single File Scan Mode
Elevate8 supports targeted file scans. Pass a single file pathway (e.g. a codebehind file); the CLI will automatically trace the nearest project root (searching for `.git`, `.csproj`, or `packages.config`), analyze the target file, and generate target reports relative to the project root:
```powershell
python Project/src/cli/main.py analyze Project/input_dotnet_legacy_code/Default.aspx.cs
```

### B. Launch Streamlit UI Dashboard
The Streamlit dashboard launches automatically at Phase 5 of the CLI process. To run it independently:
```powershell
streamlit run Project/src/ui/app.py
```

### C. Undo/Rollback a Migration
If any compilation errors occur after applying AI suggestions, you can rollback instantly. The engine reads the `rollback_manifest.json` generated in the project root and restores original files from the root `backups/` directory:
```powershell
python Project/src/cli/main.py rollback Project/input_dotnet_legacy_code
```

### D. Check Last Run Status
To quickly inspect the status and risk metrics of your last scan:
```powershell
python Project/src/cli/main.py status
```

---

## 🧪 Verification & Unit Testing

To run the suite of unit tests verifying all CLI commands, database persistence, and parser engine regexes:
```powershell
pytest Project/tests
```

---

## 🚀 Enterprise Modernization Value Proposition

Modernizing legacy enterprise C# applications to .NET 8 is a major architectural and business challenge:
*   **API Deprecation**: Core technologies like ASP.NET WebForms and WCF (Windows Communication Foundation) are obsolete and have no direct porting route in modern .NET.
*   **Manual Porting Costs**: Rewriting routes, dependency injection schemas, database access boundaries, and UI controls is time-consuming and prone to human regression.
*   **Cross-Platform Migration**: Legacy configurations rely on Windows IIS specifics (such as `Web.config` system sections) and local assembly references that prevent deploying applications in lightweight Linux Docker containers.

**Elevate8 solves this by establishing a structured, automated migration pipeline:**
1.  **Static Analysis & Dependency Resolution**: Scans namespaces, assemblies, custom packages, and configuration boundaries.
2.  **Quantitative Risk Evaluation**: Calculates an overall readiness and complexity score (0-100) based on detected obsolete dependencies and code structures.
3.  **Context-Enriched AI Translation**: Orchestrates parallel code translations using Gemini generative models, mapping legacy APIs (e.g., ViewState, WCF ServiceContracts, ConfigurationManager) directly to modern patterns (e.g., Blazor component state, Minimal API routers, constructor-injected `IConfiguration`).
4.  **Interactive Diff Review**: Generates a local Streamlit dashboard with side-by-side HTML diff visualization, rollback manifests, and audit logging to verify suggestions before writing changes to disk.

---

## 📐 System Architecture

<img width="1024" height="682" alt="image" src="https://github.com/user-attachments/assets/60566f29-1182-4a88-a7ee-454f620ae184" />



## 📁 Repository Directory Structure

The codebase is organized logically into modular components:
```text
.
├── backups/                         # Backup storage for rollback operations (isolated from MSBuild)
└── Project/
    ├── input_dotnet_legacy_code/    # Legacy source files (WebForms, WCF, Global.asax, config)
    ├── output_dotnet8_code/         # Upgraded output directory (.NET 8 Blazor, Minimal APIs, Program.cs)
    ├── tests/                       # Automated test suite (CLI, database, parser engines)
    └── src/                         # Core execution codebase
        ├── ai_engine/               # Gemini API client, JSON schema enforcement, & offline mock logic
        ├── cli/                     # CLI execution driver and CLI command entry points
        ├── database/                # SQLite local audit logging, execution logs, & prompt caching
        ├── migration_engine/        # Code rewriter, path mapper, and rollback manifest tracker
        ├── reporting/               # HTML diff viewer, PDF summary generators, and JSON reports
        ├── risk_engine/             # Quantitative risk score mapping and remediation rules
        ├── scanner/                 # AST-like regex-based scanner mapping namespaces & APIs
        └── ui/                      # Streamlit dashboard interface (premium glassmorphic theme)
```
