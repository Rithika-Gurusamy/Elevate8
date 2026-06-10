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

![Elevate8 System Architecture](system_architecture.png)


## 📁 Repository Directory Structure

The codebase is organized logically into modular components:

*   📂 [**`Project/src/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src) — Core application files:
    *   📂 [**`scanner/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/scanner) — AST-like regex scanner mapping using directives, namespaces, and technology flags.
    *   📂 [**`risk_engine/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/risk_engine) — Weighting engine mapping legacy usage to quantitative risk scores and remediation strategies.
    *   📂 [**`ai_engine/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/ai_engine) — Interface wrapper managing connections to the Gemini API, JSON schema enforcement, concurrency, rate throttling, and offline mock generation fallbacks.
    *   📂 [**`migration_engine/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/migration_engine) — Code mapping engine that restructures directory layouts, archives files to a backups database, and maintains rollback safety states.
    *   📂 [**`reporting/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/reporting) — File generator that compiles Markdown, JSON, and PDF summary sheets, and generates side-by-side HTML diffs.
    *   📂 [**`ui/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/ui) — Interactive Streamlit application customized with a premium glassmorphic dark theme.
    *   📂 [**`database/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/database) — SQLite schema manager handling local audit trails, system execution logs, and prompt-response caches.
    *   📂 [**`cli/`**](file:///c:/Users/grith/Desktop/Infinite/Project/src/cli) — Terminal-based execution driver.
*   📂 [**`Project/tests/`**](file:///c:/Users/grith/Desktop/Infinite/Project/tests) — Comprehensive unit test suites validating CLI flags, database transactions, offline blueprints, and regex AST mapping.
*   📂 [**`Project/input_dotnet_legacy_code/`**](file:///c:/Users/grith/Desktop/Infinite/Project/input_dotnet_legacy_code) — Reference legacy folder (containing WebForms, WCF contracts, `Global.asax.cs`, and legacy XML `.config` files) used to validate translation.
*   📂 [**`Project/output_dotnet8_code/`**](file:///c:/Users/grith/Desktop/Infinite/Project/output_dotnet8_code) — The target directory where modern .NET 8 outputs (Blazor components, Minimal API C# classes, `appsettings.json`, and `Program.cs`) are generated.
*   📂 [**`backups/`**](file:///c:/Users/grith/Desktop/Infinite/backups) — Target backup folder created outside the compiler path to prevent duplicate C# class definition errors.

---

## 🧠 Prompt Engineering Strategy

The translation quality relies on specialized prompt engineering architectures that enforce output constraints and inject targeted technology patterns.

The complete system templates, dynamic classification mappings, offline blueprints, and development debugging logs are documented in our dedicated prompt book:
👉 **[Read the Complete Prompt Engineering Archive & Design History](file:///c:/Users/grith/Desktop/Infinite/Prompt_Documentation.md)**

### Core Prompt Concepts
1.  **Strict JSON Output**: The assistant uses standard `response_schema` constraints to enforce JSON schema validation at the model generation layer, eliminating formatting problems like markdown code fences.
2.  **Context-Aware Injection**: The prompt dynamically appends WCF, WebForms, and MVC instructions depending on matching syntax patterns identified during Phase 1.
3.  **Hashed Caching**: Prior to calling the LLM, the prompt is hashed along with the file contents. If a match is found in the local SQLite database cache, the API call is bypassed, reducing developer latency and protecting token rate limits.

---

## 🏆 Key Technical Differentiators

*   **Offline/Online Resiliency**: Operates seamlessly in offline environments using custom migration blueprints when API keys are omitted.
*   **Build-Isolation Compliant**: Stores backups in the repository root level (`backups/`) to avoid duplicate C# class declarations within MSBuild compiler walks.
*   **High-Priority Extensibility**: Prioritizes scanning heuristics dynamically, resolving startup and application configuration mappings before applying generic controller patterns.
*   **Premium Custom Styling**: Utilizes customized CSS styles to render inputs, buttons, tables, and side-by-side navigations in an elegant, glassmorphic layout.
