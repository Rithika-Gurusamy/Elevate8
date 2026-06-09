"""
⚡ Legacy .NET Framework → .NET 8 AI Migration Assistant — Dashboard UI
Enterprise-grade Streamlit dashboard with glassmorphism design system.
"""
import os
import sys

# Add project root to sys.path to allow importing 'src' when running Streamlit directly
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import sqlite3
import json
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime
from typing import Dict, Any, List, Optional

# ─── Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title=".NET 8 Migration Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Enterprise CSS Design System ────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ────────────────────────────────── */
    .stApp {
        background: linear-gradient(145deg, #0a0e17 0%, #0d1117 30%, #0f1923 70%, #0d1117 100%);
        color: #e6edf3;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    /* ── Sidebar ───────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
        border-right: 1px solid rgba(48, 54, 61, 0.6);
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {
        color: #c9d1d9 !important;
    }

    /* ── Headers ───────────────────────────────── */
    h1, h2, h3, h4, h5, h6 {
        color: #f0f6fc !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }

    /* ── Glassmorphism Card ─────────────────────── */
    .glass-card {
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(48, 54, 61, 0.5);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
        border-color: rgba(88, 166, 255, 0.3);
        box-shadow: 0 8px 32px rgba(88, 166, 255, 0.08);
        transform: translateY(-2px);
    }

    /* ── Metric Card ───────────────────────────── */
    .metric-card {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.8) 0%, rgba(13, 17, 23, 0.9) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(48, 54, 61, 0.4);
        border-radius: 16px;
        padding: 24px 20px;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent, #58a6ff), transparent);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .metric-card:hover::before {
        opacity: 1;
    }
    .metric-card:hover {
        border-color: rgba(88, 166, 255, 0.4);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
        transform: translateY(-4px);
    }

    .metric-value {
        font-size: 36px;
        font-weight: 700;
        background: linear-gradient(135deg, #58a6ff, #79c0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 8px 0;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 11px;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    /* ── Badge System ──────────────────────────── */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .badge-low {
        background: rgba(63, 185, 80, 0.15);
        color: #3fb950;
        border: 1px solid rgba(63, 185, 80, 0.3);
    }
    .badge-medium {
        background: rgba(210, 153, 34, 0.15);
        color: #d29922;
        border: 1px solid rgba(210, 153, 34, 0.3);
    }
    .badge-high {
        background: rgba(219, 109, 40, 0.15);
        color: #db6d28;
        border: 1px solid rgba(219, 109, 40, 0.3);
    }
    .badge-critical {
        background: rgba(248, 81, 73, 0.15);
        color: #f85149;
        border: 1px solid rgba(248, 81, 73, 0.3);
    }

    /* ── Hero Banner ───────────────────────────── */
    .hero-banner {
        background: linear-gradient(135deg, rgba(31, 111, 235, 0.15) 0%, rgba(136, 58, 234, 0.10) 50%, rgba(56, 189, 248, 0.08) 100%);
        border: 1px solid rgba(48, 54, 61, 0.4);
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(88, 166, 255, 0.06), transparent 60%);
        animation: shimmer 8s ease-in-out infinite alternate;
    }
    @keyframes shimmer {
        0% { transform: translate(0%, 0%); }
        100% { transform: translate(10%, 5%); }
    }
    .hero-title {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #58a6ff, #bc8cff, #79c0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
        position: relative;
    }
    .hero-subtitle {
        color: #8b949e;
        font-size: 14px;
        position: relative;
    }

    /* ── Findings Card ─────────────────────────── */
    .finding-card {
        background: rgba(22, 27, 34, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(48, 54, 61, 0.4);
        border-left: 4px solid var(--accent, #58a6ff);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    .finding-card:hover {
        background: rgba(22, 27, 34, 0.8);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .finding-card h4 {
        margin: 0 0 8px 0;
        font-size: 16px;
    }
    .finding-card p {
        margin: 4px 0;
        color: #8b949e;
        font-size: 13px;
    }
    .finding-card code {
        background: rgba(110, 118, 129, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
        color: #79c0ff;
    }

    /* ── Divider ───────────────────────────────── */
    .divider {
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(48, 54, 61, 0.6), transparent);
        margin: 28px 0;
    }

    /* ── Progress Ring ─────────────────────────── */
    .progress-ring-container {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
    }

    /* ── Streamlit Built-in Deploy Button ── */
    div[data-testid="stHeaderAction"] button, 
    button[data-testid="stHeaderDeployButton"], 
    .stDeployButton > button {
        background: linear-gradient(135deg, #238636 0%, #2ea44f 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(46, 164, 79, 0.4) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 6px 16px !important;
        box-shadow: 0 4px 12px rgba(46, 164, 79, 0.3) !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stHeaderAction"] button:hover, 
    button[data-testid="stHeaderDeployButton"]:hover, 
    .stDeployButton > button:hover {
        background: linear-gradient(135deg, #2ea44f 0%, #3fb950 100%) !important;
        box-shadow: 0 6px 16px rgba(63, 185, 80, 0.5) !important;
        transform: translateY(-1px) !important;
        border-color: rgba(63, 185, 80, 0.6) !important;
    }

    /* ── Streamlit Tabs Overrides ── */
    button[data-baseweb="tab"] {
        color: #8b949e !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 16px !important;
        transition: all 0.2s ease !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #58a6ff !important;
        border-bottom: 2px solid #58a6ff !important;
        background: rgba(88, 166, 255, 0.05) !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #e6edf3 !important;
        background: rgba(255, 255, 255, 0.02) !important;
    }

    /* ── Streamlit Selectbox Overrides ── */
    div[data-baseweb="select"] > div {
        background-color: rgba(22, 27, 34, 0.8) !important;
        border: 1px solid rgba(48, 54, 61, 0.6) !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
        transition: all 0.2s ease !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: rgba(88, 166, 255, 0.4) !important;
    }
    div[data-baseweb="select"] span {
        color: #e6edf3 !important;
    }
    div[data-baseweb="popover"] {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="menu"] {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
    }
    div[data-baseweb="option"] {
        background-color: transparent !important;
        color: #c9d1d9 !important;
        transition: all 0.2s ease !important;
    }
    div[data-baseweb="option"]:hover, 
    div[data-baseweb="option"][aria-selected="true"] {
        background-color: rgba(88, 166, 255, 0.15) !important;
        color: #f0f6fc !important;
    }

    /* ── Streamlit Custom Button/Download Styling ── */
    div.stButton > button, 
    div.stDownloadButton > button {
        background: linear-gradient(135deg, rgba(31, 111, 235, 0.15) 0%, rgba(136, 58, 234, 0.15) 100%) !important;
        color: #e6edf3 !important;
        border: 1px solid rgba(88, 166, 255, 0.3) !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        backdrop-filter: blur(8px) !important;
    }
    div.stButton > button:hover, 
    div.stDownloadButton > button:hover {
        border-color: rgba(88, 166, 255, 0.8) !important;
        box-shadow: 0 4px 16px rgba(88, 166, 255, 0.2) !important;
        transform: translateY(-2px) !important;
        color: #ffffff !important;
    }
    div.stButton > button:active, 
    div.stDownloadButton > button:active {
        transform: translateY(0) !important;
    }

    /* Hide Streamlit branding */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

DB_PATH = "migration_assistant.db"

# ─── Database Helpers ─────────────────────────────────────────────────

def load_latest_report() -> Optional[Dict[str, Any]]:
    if not os.path.exists(DB_PATH):
        return None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, project_path, report_json, created_at FROM migration_reports ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "project_path": row[1], "report": json.loads(row[2]), "created_at": row[3]}
    except Exception as e:
        st.error(f"Error loading report: {e}")
    return None


def load_all_reports() -> List[Dict[str, Any]]:
    if not os.path.exists(DB_PATH):
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, project_path, created_at FROM migration_reports ORDER BY id DESC")
            return [{"id": r[0], "project_path": r[1], "created_at": r[2]} for r in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error loading reports: {e}")
    return []


def load_report_by_id(report_id: int) -> Optional[Dict[str, Any]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, project_path, report_json, created_at FROM migration_reports WHERE id = ?", (report_id,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "project_path": row[1], "report": json.loads(row[2]), "created_at": row[3]}
    except Exception as e:
        st.error(f"Error loading report {report_id}: {e}")
    return None


def load_logs() -> List[List[str]]:
    if not os.path.exists(DB_PATH):
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT level, message, created_at FROM migration_logs ORDER BY id DESC LIMIT 100")
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Error loading logs: {e}")
    return []


def load_audit_trail() -> List[Dict[str, Any]]:
    if not os.path.exists(DB_PATH):
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, scan_run_id, action, details, timestamp FROM audit_trail ORDER BY id DESC LIMIT 50")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error loading audit trail: {e}")
    return []


# ─── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align: center; padding: 16px 0;">
    <div style="font-size: 32px;">⚡</div>
    <div style="font-size: 18px; font-weight: 700; color: #f0f6fc; margin-top: 4px;">Migration Assistant</div>
    <div style="font-size: 12px; color: #8b949e; letter-spacing: 1px;">.NET FRAMEWORK → .NET 8</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "🛡️ Risk Analysis", "🤖 AI Suggestions", "📝 Diff Viewer", "📄 Reports", "🔍 Audit Trail", "📋 Logs"],
    label_visibility="collapsed",
)

# Load report data
all_scans = load_all_reports()
selected_report = None

if all_scans:
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Scan History")
    scan_options = {
        f"#{s['id']} · {os.path.basename(s['project_path'])} · {s['created_at'][:16]}": s["id"]
        for s in all_scans
    }
    selected_scan_name = st.sidebar.selectbox("Select scan", list(scan_options.keys()), label_visibility="collapsed")
    selected_report = load_report_by_id(scan_options[selected_scan_name])
else:
    st.sidebar.info("No scans yet. Run the CLI first.")
    # Demo data for presentation
    demo_report = {
        "id": 0,
        "project_path": "C:/Projects/LegacyApp",
        "created_at": datetime.now().isoformat(),
        "report": {
            "metadata": {"total_files": 8, "estimated_effort": "2-4 Weeks (High Effort)", "readiness_percentage": 28},
            "risk_report": {
                "risk_score": 72, "risk_category": "High",
                "findings": [
                    {"indicator": "WCF", "impact": "High", "count": 5, "files": ["Services/OrderService.svc", "Services/OrderService.svc.cs"], "remediation": "WCF is not supported in .NET 8. Migrate to gRPC, CoreWCF, or ASP.NET Core Minimal APIs."},
                    {"indicator": "WebForms", "impact": "Critical", "count": 14, "files": ["Default.aspx", "Default.aspx.cs", "Login.aspx", "Login.aspx.cs"], "remediation": "WebForms is not supported in .NET 8. Rewrite using Blazor, Razor Pages, or React SPA with Web API."},
                    {"indicator": "System.Web", "impact": "Medium", "count": 22, "files": ["Controllers/HomeController.cs", "Global.asax.cs", "Default.aspx.cs"], "remediation": "Replace HttpContext.Current with IHttpContextAccessor via dependency injection."},
                    {"indicator": "Legacy Packages", "impact": "Medium", "count": 6, "files": ["packages.config"], "remediation": "Upgrade EntityFramework to EF Core, log4net to Serilog/NLog for .NET 8."},
                    {"indicator": "Config Complexity", "impact": "Low", "count": 2, "files": ["Web.config"], "remediation": "Migrate Web.config to appsettings.json and Program.cs configuration."},
                ],
                "legacy_packages": ["EntityFramework", "log4net", "Microsoft.AspNet.WebApi", "Microsoft.AspNet.Mvc", "AjaxControlToolkit"],
                "unsupported_apis": ["HttpContext.Current", "System.Web.UI.Page", "System.ServiceModel.*", "ConfigurationManager", "ViewState", "HttpApplication"],
                "config_complexity_details": {"config_files_count": 2, "has_system_web_config": True, "has_wcf_config": True},
            },
            "ai_suggestions": {
                "Services/OrderService.svc.cs": {
                    "file_path": "Services/OrderService.svc.cs",
                    "summary": "WCF service with [ServiceContract] and [OperationContract] using ADO.NET and ConfigurationManager.",
                    "migration_strategy": "1. Replace WCF contracts with Minimal API endpoints.\n2. Replace ADO.NET with EF Core.\n3. Replace ConfigurationManager with IConfiguration.",
                    "unsupported_apis": ["ServiceContractAttribute", "OperationContractAttribute", "ConfigurationManager"],
                    "dotnet8_equivalent": "public static class OrderEndpoints\n{\n    public static RouteGroupBuilder MapOrderEndpoints(this RouteGroupBuilder group)\n    {\n        group.MapGet(\"/\", async (AppDbContext db) =>\n            await db.Orders.ToListAsync());\n        group.MapPost(\"/\", async (CreateOrderRequest req, AppDbContext db) => {\n            db.Orders.Add(new Order { ... });\n            await db.SaveChangesAsync();\n        });\n        return group;\n    }\n}",
                    "code_diff_markdown": "- [ServiceContract]\n- public interface IOrderService { ... }\n+ public static class OrderEndpoints { ... }",
                    "confidence_score": 0.78,
                },
                "Default.aspx.cs": {
                    "file_path": "Default.aspx.cs",
                    "summary": "WebForms code-behind using Page_Load, ViewState, Session, HttpContext.Current, and ADO.NET.",
                    "migration_strategy": "1. Convert to Blazor component.\n2. Replace Page_Load with OnInitializedAsync.\n3. Replace ViewState with component state.\n4. Replace HttpContext.Current with IHttpContextAccessor.",
                    "unsupported_apis": ["System.Web.UI.Page", "ViewState", "HttpContext.Current", "Session"],
                    "dotnet8_equivalent": "@page \"/\"\n@inject AppDbContext Db\n@inject IHttpContextAccessor Ctx\n\n@code {\n    private List<OrderDto> orders = new();\n    protected override async Task OnInitializedAsync()\n    {\n        orders = await Db.Orders.ToListAsync();\n    }\n}",
                    "code_diff_markdown": "- public partial class Default : System.Web.UI.Page\n- { Page_Load(...) { ... } }\n+ @page \"/\"\n+ @code { OnInitializedAsync() { ... } }",
                    "confidence_score": 0.74,
                },
                "Controllers/HomeController.cs": {
                    "file_path": "Controllers/HomeController.cs",
                    "summary": "ASP.NET MVC controller using HttpContext.Current, Cache API, Session, Application state.",
                    "migration_strategy": "1. Replace System.Web.Mvc.Controller with Microsoft.AspNetCore.Mvc.Controller.\n2. Replace HttpContext.Current with IHttpContextAccessor.\n3. Replace Cache with IMemoryCache.\n4. Replace ConfigurationManager with IConfiguration.",
                    "unsupported_apis": ["HttpContext.Current", "System.Web.Caching.Cache", "System.Web.Mvc.Controller"],
                    "dotnet8_equivalent": "public class HomeController : Controller\n{\n    private readonly IHttpContextAccessor _ctx;\n    private readonly IMemoryCache _cache;\n    public HomeController(IHttpContextAccessor ctx, IMemoryCache cache) { ... }\n}",
                    "code_diff_markdown": "- using System.Web;\n- HttpContext.Current.Cache[\"key\"] = value;\n+ using Microsoft.Extensions.Caching.Memory;\n+ _cache.Set(\"key\", value, TimeSpan.FromMinutes(5));",
                    "confidence_score": 0.85,
                },
            },
        },
    }
    selected_report = demo_report

# ─── Extract Report Data ──────────────────────────────────────────────
project_path = selected_report["project_path"]
report_data = selected_report["report"]
risk_report = report_data["risk_report"]
metadata = report_data.get("metadata", {})
ai_suggestions = report_data.get("ai_suggestions", {})

score = risk_report["risk_score"]
category = risk_report["risk_category"]
readiness = max(0, 100 - score)

badge_map = {"Low": "low", "Medium": "medium", "High": "high", "Critical": "critical"}
badge_class = badge_map.get(category, "medium")
accent_map = {"Low": "#3fb950", "Medium": "#d29922", "High": "#db6d28", "Critical": "#f85149"}
accent = accent_map.get(category, "#58a6ff")


# ═══════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════

if menu == "📊 Dashboard":
    # ── Hero Banner ────────────────────────────────────────────
    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-title">⚡ .NET 8 Migration Assistant</div>
        <div class="hero-subtitle">Analyzing: <strong>{os.path.basename(project_path)}</strong> &nbsp;·&nbsp;
        Scanned at {selected_report['created_at'][:19]}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metric Cards ───────────────────────────────────────────
    cols = st.columns(5)
    
    total_files = metadata.get("total_files", len(report_data.get("project_analysis", {}).get("files", [])) or len(ai_suggestions))

    wcf_cnt = sum(1 for f in risk_report.get("findings", []) if f["indicator"] == "WCF" for _ in [f["count"]])
    wf_cnt = sum(1 for f in risk_report.get("findings", []) if f["indicator"] == "WebForms" for _ in [f["count"]])
    for f in risk_report.get("findings", []):
        if f["indicator"] == "WCF": wcf_cnt = f["count"]
        if f["indicator"] == "WebForms": wf_cnt = f["count"]

    metrics = [
        ("Total Files", str(total_files), "#58a6ff"),
        ("Risk Score", f'<span class="badge badge-{badge_class}">{score}/100</span>', accent),
        ("WCF Services", str(wcf_cnt), "#f85149"),
        ("WebForms", str(wf_cnt), "#bc8cff"),
        ("Readiness", f"{readiness}%", "#3fb950"),
    ]

    for col, (label, value, color) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card" style="--accent: {color};">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="background: linear-gradient(135deg, {color}, {color}dd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Charts Row ─────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        st.markdown("##### Risk Score Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 36, "color": "#f0f6fc"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#30363d", "tickfont": {"color": "#8b949e"}},
                "bar": {"color": accent, "thickness": 0.7},
                "bgcolor": "rgba(22,27,34,0.5)",
                "bordercolor": "#30363d",
                "steps": [
                    {"range": [0, 30], "color": "rgba(63,185,80,0.1)"},
                    {"range": [30, 60], "color": "rgba(210,153,34,0.1)"},
                    {"range": [60, 80], "color": "rgba(219,109,40,0.1)"},
                    {"range": [80, 100], "color": "rgba(248,81,73,0.1)"},
                ],
                "threshold": {"line": {"color": "#f0f6fc", "width": 3}, "thickness": 0.8, "value": score},
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#8b949e"}, height=280,
            margin=dict(t=30, b=10, l=30, r=30),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with c2:
        st.markdown("##### Risk Distribution")
        finding_labels = [f["indicator"] for f in risk_report.get("findings", [])]
        finding_counts = [f["count"] for f in risk_report.get("findings", [])]
        colors = ["#f85149", "#bc8cff", "#d29922", "#58a6ff", "#3fb950"]

        if finding_labels:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=finding_counts + [finding_counts[0]],
                theta=finding_labels + [finding_labels[0]],
                fill="toself",
                fillcolor="rgba(88,166,255,0.15)",
                line=dict(color="#58a6ff", width=2),
                marker=dict(size=6, color="#58a6ff"),
            ))
            fig_radar.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, color="#30363d", gridcolor="rgba(48,54,61,0.3)"),
                    angularaxis=dict(color="#8b949e", gridcolor="rgba(48,54,61,0.3)"),
                ),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8b949e"), height=280, showlegend=False,
                margin=dict(t=30, b=30, l=60, r=60),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with c3:
        st.markdown("##### Technology Breakdown")
        tech_data = {}
        for f in risk_report.get("findings", []):
            tech_data[f["indicator"]] = f["count"]
        if tech_data:
            fig_donut = go.Figure(go.Pie(
                labels=list(tech_data.keys()),
                values=list(tech_data.values()),
                hole=0.55,
                marker=dict(colors=colors[:len(tech_data)], line=dict(color="#0d1117", width=2)),
                textinfo="label+percent",
                textfont=dict(size=11, color="#e6edf3"),
            ))
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8b949e"), height=280, showlegend=False,
                margin=dict(t=30, b=30, l=10, r=10),
                annotations=[dict(text=f"<b>{len(tech_data)}</b><br>Types", x=0.5, y=0.5, font_size=14, font_color="#8b949e", showarrow=False)],
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    # ── Complexity Breakdown Bar ───────────────────────────────
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("##### Migration Complexity Weights")

    weight_labels = ["WCF (w=30)", "WebForms (w=30)", "System.Web (w=20)", "Legacy Pkgs (w=10)", "Config (w=10)"]
    weight_vals = [
        min(30, 30 if wcf_cnt > 0 else 0),
        min(30, 30 if wf_cnt > 0 else 0),
        min(20, 20 if any(f["indicator"] == "System.Web" for f in risk_report.get("findings", [])) else 0),
        min(10, 10 if risk_report.get("legacy_packages") else 0),
        min(10, 10 if risk_report.get("config_complexity_details", {}).get("config_files_count", 0) > 0 else 0),
    ]
    bar_colors = ["#f85149", "#bc8cff", "#d29922", "#58a6ff", "#3fb950"]

    fig_bar = go.Figure(go.Bar(
        x=weight_vals, y=weight_labels, orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{v}" for v in weight_vals], textposition="inside", textfont=dict(color="#f0f6fc", size=12),
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8b949e"), height=220,
        xaxis=dict(range=[0, 35], gridcolor="rgba(48,54,61,0.2)", showgrid=True),
        yaxis=dict(autorange="reversed"),
        margin=dict(t=10, b=20, l=10, r=20), bargap=0.35,
    )
    st.plotly_chart(fig_bar, use_container_width=True)


elif menu == "🛡️ Risk Analysis":
    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-title">🛡️ Risk Analysis Report</div>
        <div class="hero-subtitle">Overall Rating: <span class="badge badge-{badge_class}">{category}</span> &nbsp;·&nbsp; Score: {score}/100</div>
    </div>
    """, unsafe_allow_html=True)

    st.progress(score / 100.0)

    st.markdown("### Detected Migration Blockers")
    impact_colors = {"Critical": "#f85149", "High": "#db6d28", "Medium": "#d29922", "Low": "#3fb950"}

    for finding in risk_report.get("findings", []):
        ic = impact_colors.get(finding["impact"], "#58a6ff")
        files_html = "".join(f"<code>{f}</code> " for f in finding["files"])
        st.markdown(f"""
        <div class="finding-card" style="--accent: {ic};">
            <h4 style="color: {ic};">[{finding['impact']}] {finding['indicator']}</h4>
            <p><strong>Occurrences:</strong> {finding['count']}</p>
            <p><strong>Remediation:</strong> {finding['remediation']}</p>
            <p><strong>Files:</strong> {files_html}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### Unsupported Legacy APIs")
    unsupported = risk_report.get("unsupported_apis", [])
    if unsupported:
        api_cols = st.columns(3)
        for i, api in enumerate(unsupported):
            with api_cols[i % 3]:
                st.markdown(f"""
                <div class="glass-card" style="padding: 12px 16px; text-align: center;">
                    <code style="color: #f85149; font-size: 13px;">{api}</code>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("No unsupported APIs detected.")


elif menu == "🤖 AI Suggestions":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🤖 AI Migration Suggestions</div>
        <div class="hero-subtitle">Gemini-powered analysis with confidence scoring</div>
    </div>
    """, unsafe_allow_html=True)

    if not ai_suggestions:
        st.warning("No suggestions generated. Run the CLI analyzer first.")
    else:
        selected_file = st.selectbox("Select file to review", list(ai_suggestions.keys()))
        sug = ai_suggestions[selected_file]

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"""
            <div class="glass-card">
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #8b949e; margin-bottom: 12px;">Migration Summary</div>
                <p style="color: #e6edf3; line-height: 1.6;">{sug['summary']}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### Migration Strategy")
            st.info(sug["migration_strategy"])

            st.markdown("##### Unsupported APIs")
            for api in sug.get("unsupported_apis", []):
                st.markdown(f"- `{api}`")

            conf = sug.get("confidence_score", 0.0)
            conf_color = "#3fb950" if conf >= 0.8 else ("#d29922" if conf >= 0.5 else "#f85149")
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; --accent: {conf_color};">
                <div class="metric-label">AI Confidence</div>
                <div class="metric-value" style="font-size: 42px; background: {conf_color}; -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{conf*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("##### Recommended .NET 8 Equivalent")
            st.code(sug.get("dotnet8_equivalent", ""), language="csharp")


elif menu == "📝 Diff Viewer":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">📝 Diff Viewer</div>
        <div class="hero-subtitle">Side-by-side comparison of legacy vs modern .NET 8 code</div>
    </div>
    """, unsafe_allow_html=True)

    if not ai_suggestions:
        st.warning("No suggestions available for diff comparison.")
    else:
        selected_file = st.selectbox("Select file", list(ai_suggestions.keys()))
        sug = ai_suggestions[selected_file]

        tab1, tab2 = st.tabs(["📋 Git Diff", "🔀 Side-by-Side HTML"])

        with tab1:
            st.code(sug.get("code_diff_markdown", ""), language="diff")

        with tab2:
            from src.reporting.diff_generator import DiffGenerator

            orig_code = ""
            full_path = os.path.join(project_path, selected_file)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        orig_code = f.read()
                except Exception:
                    pass

            if not orig_code:
                orig_code = "// Original source not available. Run CLI scan with local project path."

            diff_gen = DiffGenerator()
            html_content = diff_gen.generate_html_diff(orig_code, sug.get("dotnet8_equivalent", ""), selected_file)

            # Inject dark theme into the HTML diff
            dark_css = """
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                
                body { background: #0d1117 !important; color: #e6edf3 !important; font-family: 'Consolas', monospace; }
                table.diff { background: #0d1117; border-collapse: collapse; width: 100%; font-size: 12px; }
                td { padding: 4px 8px; border: 1px solid #21262d; }
                .diff_header { background: #161b22; color: #8b949e; }
                
                /* Diff Navigation Buttons styling */
                .diff_next { background: #161b22; text-align: center; }
                .diff_next a {
                    display: inline-block !important;
                    padding: 3px 8px !important;
                    background: linear-gradient(135deg, #1f6feb 0%, #38bdf8 100%) !important;
                    color: #ffffff !important;
                    text-decoration: none !important;
                    border-radius: 4px !important;
                    font-size: 10px !important;
                    font-weight: bold !important;
                    text-transform: uppercase !important;
                    transition: all 0.2s ease-in-out !important;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3) !important;
                    margin: 1px !important;
                    border: 1px solid rgba(88, 166, 255, 0.4) !important;
                }
                .diff_next a:hover {
                    background: linear-gradient(135deg, #38bdf8 0%, #1f6feb 100%) !important;
                    transform: scale(1.1) translateY(-1px) !important;
                    box-shadow: 0 4px 8px rgba(56, 189, 248, 0.4) !important;
                    color: #ffffff !important;
                }
                
                .diff_add { background: rgba(63,185,80,0.15); color: #3fb950; }
                .diff_chg { background: rgba(210,153,34,0.15); color: #d29922; }
                .diff_sub { background: rgba(248,81,73,0.15); color: #f85149; }
                td:first-child, td:nth-child(2) { color: #484f58; text-align: right; width: 40px; }
                
                /* Legends box container styling */
                table[summary="Legends"] {
                    background: rgba(22, 27, 34, 0.8) !important;
                    backdrop-filter: blur(12px) !important;
                    -webkit-backdrop-filter: blur(12px) !important;
                    border: 1px solid rgba(48, 54, 61, 0.7) !important;
                    border-radius: 12px !important;
                    margin: 32px auto 16px auto !important;
                    max-width: 900px !important;
                    width: 100% !important;
                    color: #e6edf3 !important;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
                    border-collapse: separate !important;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
                    overflow: hidden !important;
                }
                table[summary="Legends"] th {
                    background: linear-gradient(90deg, #161b22, #21262d) !important;
                    color: #f0f6fc !important;
                    font-size: 14px !important;
                    font-weight: 600 !important;
                    letter-spacing: 0.5px !important;
                    padding: 12px 20px !important;
                    border-bottom: 1px solid rgba(48, 54, 61, 0.6) !important;
                    text-align: left !important;
                }
                table[summary="Legends"] td {
                    border: none !important;
                    padding: 16px 20px !important;
                }
                
                /* Inside Legends tables styling */
                table[summary="Colors"], table[summary="Links"] {
                    background: transparent !important;
                    border-collapse: collapse !important;
                    width: 100% !important;
                }
                table[summary="Colors"] th, table[summary="Links"] th {
                    border-bottom: 1px solid rgba(48, 54, 61, 0.4) !important;
                    color: #8b949e !important;
                    font-size: 12px !important;
                    font-weight: 600 !important;
                    text-transform: uppercase !important;
                    letter-spacing: 1px !important;
                    padding-bottom: 8px !important;
                    background: transparent !important;
                }
                table[summary="Colors"] td {
                    padding: 6px 12px !important;
                    border-radius: 6px !important;
                    font-size: 12px !important;
                    font-weight: 600 !important;
                    text-align: center !important;
                    margin-top: 8px !important;
                    display: inline-block !important;
                    width: 110px !important;
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
                }
                
                table[summary="Colors"] td.diff_add {
                    background: rgba(63, 185, 80, 0.15) !important;
                    color: #3fb950 !important;
                    border: 1px solid rgba(63, 185, 80, 0.3) !important;
                }
                table[summary="Colors"] td.diff_chg {
                    background: rgba(210, 153, 34, 0.15) !important;
                    color: #d29922 !important;
                    border: 1px solid rgba(210, 153, 34, 0.3) !important;
                }
                table[summary="Colors"] td.diff_sub {
                    background: rgba(248, 81, 73, 0.15) !important;
                    color: #f85149 !important;
                    border: 1px solid rgba(248, 81, 73, 0.3) !important;
                }
                
                table[summary="Links"] td {
                    color: #c9d1d9 !important;
                    font-size: 13px !important;
                    line-height: 1.6 !important;
                    padding: 8px 0 !important;
                }
            </style>
            """
            html_content = html_content.replace("</head>", dark_css + "</head>")
            components.html(html_content, height=600, scrolling=True)


elif menu == "📄 Reports":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">📄 Migration Reports</div>
        <div class="hero-subtitle">Download and review generated reports</div>
    </div>
    """, unsafe_allow_html=True)

    from src.reporting.diff_generator import DiffGenerator
    from src.risk_engine.models import MigrationRiskReport, RiskFinding
    from src.ai_engine.models import ProjectMigrationSuggestion, FileMigrationSuggestion

    original_contents = {}
    for f_key in ai_suggestions.keys():
        full_path = os.path.join(project_path, f_key)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as fobj:
                    original_contents[f_key] = fobj.read()
            except Exception:
                original_contents[f_key] = ""

    rec_findings = [
        RiskFinding(indicator=f["indicator"], impact=f["impact"], count=f["count"],
                    files=f["files"], remediation=f["remediation"])
        for f in risk_report.get("findings", [])
    ]
    rep_obj = MigrationRiskReport(
        risk_score=score, risk_category=category, findings=rec_findings,
        legacy_packages=risk_report.get("legacy_packages", []),
        unsupported_apis=risk_report.get("unsupported_apis", []),
        config_complexity_details=risk_report.get("config_complexity_details", {}),
    )
    sug_dict = {
        path: FileMigrationSuggestion(
            file_path=s["file_path"], summary=s["summary"],
            migration_strategy=s["migration_strategy"],
            unsupported_apis=s.get("unsupported_apis", []),
            dotnet8_equivalent=s.get("dotnet8_equivalent", ""),
            code_diff_markdown=s.get("code_diff_markdown", ""),
            confidence_score=s.get("confidence_score", 0.0),
        )
        for path, s in ai_suggestions.items()
    }
    suggestions_obj = ProjectMigrationSuggestion(suggestions=sug_dict)

    diff_gen = DiffGenerator()
    report_md = diff_gen.generate_migration_report_markdown(project_path, rep_obj, suggestions_obj, original_contents)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button("📥 Download Markdown Report", data=report_md, file_name="migration_report.md", mime="text/markdown", use_container_width=True)
    with dl_col2:
        report_json = json.dumps(report_data, indent=2, default=str)
        st.download_button("📥 Download JSON Report", data=report_json, file_name="migration_report.json", mime="application/json", use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### Report Preview")
    st.markdown(report_md)


elif menu == "🔍 Audit Trail":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🔍 Audit Trail</div>
        <div class="hero-subtitle">Complete history of migration decisions and actions</div>
    </div>
    """, unsafe_allow_html=True)

    audit_data = load_audit_trail()
    if not audit_data:
        st.info("No audit trail entries yet. Actions are recorded when you create backups, apply migrations, or perform rollbacks.")
    else:
        for entry in audit_data:
            action_icons = {"BACKUP_CREATED": "💾", "MIGRATION_APPLIED": "🚀", "ROLLBACK": "⏪"}
            icon = action_icons.get(entry["action"], "📌")
            st.markdown(f"""
            <div class="finding-card" style="--accent: #58a6ff;">
                <h4>{icon} {entry['action']}</h4>
                <p><strong>Scan Run:</strong> #{entry.get('scan_run_id', 'N/A')}</p>
                <p><strong>Details:</strong> {entry['details']}</p>
                <p style="color: #484f58; font-size: 11px;">{entry['timestamp']}</p>
            </div>
            """, unsafe_allow_html=True)


elif menu == "📋 Logs":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">📋 System Logs</div>
        <div class="hero-subtitle">Execution history and diagnostic messages</div>
    </div>
    """, unsafe_allow_html=True)

    log_rows = load_logs()
    if not log_rows:
        st.info("No log entries found.")
    else:
        level_colors = {"INFO": "#3fb950", "WARNING": "#d29922", "ERROR": "#f85149", "DEBUG": "#8b949e"}
        for row in log_rows[:50]:
            level, msg, ts = row
            lc = level_colors.get(level, "#8b949e")
            st.markdown(f"""
            <div style="padding: 8px 16px; border-left: 3px solid {lc}; background: rgba(22,27,34,0.4); margin-bottom: 4px; border-radius: 0 4px 4px 0; font-size: 13px;">
                <span style="color: {lc}; font-weight: 600; font-size: 11px; text-transform: uppercase;">{level}</span>
                <span style="color: #484f58; margin: 0 8px;">·</span>
                <span style="color: #8b949e; font-size: 11px;">{ts[:19] if ts else ''}</span>
                <br/>
                <span style="color: #e6edf3;">{msg}</span>
            </div>
            """, unsafe_allow_html=True)
