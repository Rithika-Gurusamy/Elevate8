# .NET 8 AI Migration Assistant Report
**Target Project**: `C:\Users\grith\Desktop\Infinite\demo_project`  
**Report Generated**: `2026-06-09 10:32:59`  
**Migration Readiness**: `29%`  
**Overall Risk Rating**: `High (71/100)`  
**Estimated Migration Effort**: `2-4 Weeks (High Effort)`  

## 1. Executive Summary
This report summarizes the scans and risk assessments of porting the legacy .NET project to modern .NET 8. 
Out of the files analyzed, we identified several structural migration barriers including WCF, WebForms, or outdated package dependencies.


## 2. Migration Roadmap
To migrate this project to .NET 8, the following roadmap is recommended:
1. **Preparation**: Create a full backup of the source codebase.
2. **Infrastructure**: Upgrade the project SDK version in `.csproj` files to target `net8.0` and clean up configuration files.
3. **Dependency Cleanup**: Replace or upgrade unsupported NuGet packages (e.g. migrate EntityFramework to EF Core).
4. **Service Rewrite**: Migrate legacy endpoints (e.g., WCF services to gRPC/Minimal APIs, and WebForms UI pages to Blazor or Razor Pages).
5. **Validation**: Execute integration and build validation pipelines.


## 3. Risk Assessment & Blockers
### [High Risk] WCF
- **Occurrences**: 4
- **Remediation Recommendation**: WCF is not natively supported in .NET 8. Migrate services to gRPC, CoreWCF, or ASP.NET Core Minimal APIs.
- **Impacted Files**:
  - `Web.config`
  - `Services\OrderService.svc`
  - `Services\OrderService.svc.cs`

### [Critical Risk] WebForms
- **Occurrences**: 5
- **Remediation Recommendation**: ASP.NET WebForms is not supported in .NET 8. Rewrite interface components using ASP.NET Core Razor Pages, Blazor, or a modern SPA framework (React/Vue) with Web API.
- **Impacted Files**:
  - `Default.aspx`
  - `Default.aspx.cs`
  - `Global.asax`

### [Medium Risk] System.Web
- **Occurrences**: 6
- **Remediation Recommendation**: System.Web is deprecated. Replace HttpContext.Current usage with dependency injection of IHttpContextAccessor. Migrate handlers/modules to ASP.NET Core Middleware.
- **Impacted Files**:
  - `Default.aspx.cs`
  - `Global.asax.cs`
  - `Controllers\HomeController.cs`

### [Medium Risk] Legacy Packages
- **Occurrences**: 9
- **Remediation Recommendation**: Upgrade legacy NuGet packages to modern versions targeting .NET 8. Legacy packages found: EntityFramework, log4net, Microsoft.AspNet.Mvc, Microsoft.AspNet.Razor, Microsoft.AspNet.WebApi, Microsoft.AspNet.WebPages, Microsoft.AspNet.Web.Optimization, AutoFac.Mvc5, AjaxControlToolkit
- **Impacted Files**:
  - `LegacyApp.csproj`
  - `packages.config`

### [Low Risk] Config Complexity
- **Occurrences**: 2
- **Remediation Recommendation**: Convert XML configurations (Web.config/App.config) to JSON-based appsettings.json. Migrate WCF endpoint configurations to code-based initialization.
- **Impacted Files**:
  - `packages.config`
  - `Web.config`



## 4. Unsupported Legacy APIs
- `HttpContext.Current`
- `System.Web.* namespaces`
- `System.ServiceModel.* namespaces`



## 5. File-by-File AI Suggestions & Diffs
### File: `Default.aspx.cs`
**Summary**: WebForms code-behind 'Default.aspx.cs' with Page_Load lifecycle, ViewState usage, Session state, HttpContext.Current access, and direct ADO.NET database operations.  
**Migration Plan**: 1. Convert Page class to a Blazor component @code block.
2. Replace Page_Load with OnInitializedAsync().
3. Replace ViewState with component-level fields/properties.
4. Replace Session access with IDistributedCache or cascading parameters.
5. Replace HttpContext.Current with injected IHttpContextAccessor.
6. Replace SqlConnection/SqlCommand with EF Core DbContext.  
**AI Confidence**: `74.0%`  

**Git Diff Summary**:
```diff
--- a/Default.aspx.cs
+++ b/Default.aspx.cs
@@ -1,135 +1,38 @@
-using System;
-using System.Collections.Generic;
-using System.Data;
-using System.Data.SqlClient;
-using System.Configuration;
-using System.Web;
-using System.Web.UI;
-using System.Web.UI.WebControls;
+@page "/"
+@using Microsoft.AspNetCore.Http
+@using Microsoft.EntityFrameworkCore
+@inject AppDbContext Db
+@inject IHttpContextAccessor HttpContextAccessor
+@inject NavigationManager NavigationManager
 
-namespace LegacyApp
-{
-    public partial class Default : System.Web.UI.Page
+<PageTitle>Dashboard</PageTitle>
+
+@code {
+    private List<OrderDto> orders = new();
+    private string currentUser = "";
+    private int totalOrders;
+    private decimal totalRevenue;
+
+    protected override async Task OnInitializedAsync()
     {
-        protected void Page_Load(object sender, EventArgs e)
-        {
-            if (!IsPostBack)
-            {
-                // Check authentication via HttpContext
-                if (HttpContext.Current.User == null || !HttpContext.Current.User.Identity.IsAuthenticated)
-                {
-                    Response.Redirect("~/Login.aspx");
-                    return;
-                }
+        // Replaces HttpContext.Current.User
+        currentUser = HttpContextAccessor.HttpContext?.User?.Identity?.Name ?? "Anonymous";
 
-                // Store user info in ViewState
-                ViewState["CurrentUser"] = HttpContext.Current.User.Identity.Name;
-                ViewState["LoginTime"] = DateTime.Now;
+        // Replaces ViewState + Page_Load data binding
+        orders = await Db.Orders
+            .Include(o => o.Customer)
+            .OrderByDescending(o => o.OrderDate)
+            .Take(100)
+            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
+            .ToListAsync();
 
-                // Log page access using Session
-                Session["LastPageVisited"] = "Default.aspx";
-                Session["PageAccessCount"] = (int)(Session["PageAccessCount"] ?? 0) + 1;
+        var summary = await Db.Orders
+            .Where(o => o.OrderDate.Year == DateTime.Now.Year)
+            .GroupBy(_ => 1)
+            .Select(g => new { Count = g.Count(), Revenue = g.Sum(o => o.TotalAmount) })
+            .FirstOrDefaultAsync();
 
-                BindOrdersGrid();
-                LoadDashboardSummary();
-            }
-        }
-
-        private void BindOrdersGrid()
-        {
-            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
-            using (SqlConnection conn = new SqlConnection(connStr))
-            {
-                conn.Open();
-                string query = @"
-                    SELECT TOP 100 
-                        o.OrderId, c.CustomerName, o.OrderDate, 
-                        o.TotalAmount, o.Status
-                    FROM Orders o 
-                    INNER JOIN Customers c ON o.CustomerId = c.CustomerId
-                    ORDER BY o.OrderDate DESC";
-
-                SqlCommand cmd = new SqlCommand(query, conn);
-                SqlDataAdapter da = new SqlDataAdapter(cmd);
-                DataTable dt = new DataTable();
-                da.Fill(dt);
-
-                OrdersGrid.DataSource = dt;
-                OrdersGrid.DataBind();
-            }
-        }
-
-        private void LoadDashboardSummary()
-        {
-            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
-            using (SqlConnection conn = new SqlConnection(connStr))
-            {
-                conn.Open();
-                SqlCommand cmd = new SqlCommand(
-                    "SELECT COUNT(*) AS TotalOrders, SUM(TotalAmount) AS Revenue FROM Orders WHERE YEAR(OrderDate) = YEAR(GETDATE())",
-                    conn);
-                SqlDataReader reader = cmd.ExecuteReader();
-                if (reader.Read())
-                {
-                    lblTotalOrders.Text = $"Total Orders: {reader["TotalOrders"]}";
-                    lblTotalRevenue.Text = $"Revenue: {reader["Revenue"]:C}";
-                }
-            }
-        }
-
-        protected void OrdersGrid_RowCommand(object sender, GridViewCommandEventArgs e)
-        {
-            if (e.CommandName == "ViewOrder")
-            {
-                int rowIndex = Convert.ToInt32(e.CommandArgument);
-                string orderId = OrdersGrid.DataKeys[rowIndex].Value.ToString();
-
-                // Use HttpContext.Current to store state between pages
-                HttpContext.Current.Items["SelectedOrderId"] = orderId;
-                Response.Redirect($"~/OrderDetails.aspx?id={orderId}");
-            }
-        }
-
-        protected void OrdersGrid_PageIndexChanging(object sender, GridViewPageEventArgs e)
-        {
-            OrdersGrid.PageIndex = e.NewPageIndex;
-            BindOrdersGrid();
-        }
-
-        protected void btnRefresh_Click(object sender, EventArgs e)
-        {
-            BindOrdersGrid();
-            LoadDashboardSummary();
-        }
-
-        protected void btnExport_Click(object sender, EventArgs e)
-        {
-            // Legacy pattern: writing directly to HttpResponse
-            Response.Clear();
-            Response.ContentType = "application/vnd.ms-excel";
-            Response.AddHeader("Content-Disposition", "attachment; filename=Orders.xls");
-
-            System.IO.StringWriter sw = new System.IO.StringWriter();
-            HtmlTextWriter hw = new HtmlTextWriter(sw);
-            OrdersGrid.RenderControl(hw);
-            Response.Write(sw.ToString());
-            Response.End();
-        }
-
-        protected string GetStatusCssClass(string status)
-        {
-            switch (status)
-            {
-                case "Completed": return "badge badge-success";
-                case "Pending": return "badge badge-warning";
-                case "Cancelled": return "badge badge-danger";
-                default: return "badge badge-secondary";
-            }
-        }
-
-        public override void VerifyRenderingInServerForm(Control control)
-        {
-            // Required for Excel export of GridView
-        }
+        totalOrders = summary?.Count ?? 0;
+        totalRevenue = summary?.Revenue ?? 0;
     }
 }
```

---
### File: `Global.asax.cs`
**Summary**: ASP.NET Global Application file 'Global.asax.cs' implementing HttpApplication lifecycle events (Application_Start, Application_BeginRequest, Application_Error, Session_Start).  
**Migration Plan**: 1. Move Application_Start logic to Program.cs builder configuration.
2. Replace Application_BeginRequest/EndRequest with ASP.NET Core middleware.
3. Replace Application_Error with app.UseExceptionHandler() middleware.
4. Replace Session_Start with session configuration in Program.cs.
5. Replace Application/Session state with DI-registered singleton/scoped services.  
**AI Confidence**: `90.0%`  

**Git Diff Summary**:
```diff
--- a/Global.asax.cs
+++ b/Global.asax.cs
@@ -1,66 +1,60 @@
-using System;
-using System.Web;
-using System.Web.Mvc;
-using System.Web.Routing;
-using System.Web.Http;
-using System.Web.Optimization;
+// Program.cs — replaces Global.asax.cs entirely
 
-namespace LegacyApp
+using LegacyApp.Middleware;
+
+var builder = WebApplication.CreateBuilder(args);
+
+// Service registration (replaces Application_Start)
+builder.Services.AddControllersWithViews();
+builder.Services.AddDbContext<AppDbContext>(o =>
+    o.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
+builder.Services.AddMemoryCache();
+builder.Services.AddSession(o => o.IdleTimeout = TimeSpan.FromMinutes(20));
+builder.Services.AddSingleton<IAppMetrics, AppMetrics>();
+
+var app = builder.Build();
+
+// Middleware pipeline (replaces Application_BeginRequest/EndRequest)
+app.UseMiddleware<RequestTimingMiddleware>();
+app.UseExceptionHandler("/Error");
+app.UseHsts();
+app.UseHttpsRedirection();
+app.UseStaticFiles();
+app.UseRouting();
+app.UseAuthentication();
+app.UseAuthorization();
+app.UseSession();
+app.MapControllerRoute("default", "{controller=Home}/{action=Index}/{id?}");
+
+app.Run();
+
+// RequestTimingMiddleware.cs — replaces Application_BeginRequest/EndRequest
+namespace LegacyApp.Middleware;
+
+/// <summary>Middleware that logs slow requests (replaces HttpApplication events).</summary>
+public class RequestTimingMiddleware
 {
-    public class MvcApplication : System.Web.HttpApplication
+    private readonly RequestDelegate _next;
+    private readonly ILogger<RequestTimingMiddleware> _logger;
+
+    public RequestTimingMiddleware(RequestDelegate next, ILogger<RequestTimingMiddleware> logger)
     {
-        protected void Application_Start()
+        _next = next;
+        _logger = logger;
+    }
+
+    public async Task InvokeAsync(HttpContext context, IAppMetrics metrics)
+    {
+        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
+        metrics.IncrementRequestCount();
+
+        await _next(context);
+
+        stopwatch.Stop();
+        if (stopwatch.ElapsedMilliseconds > 500)
         {
-            AreaRegistration.RegisterAllAreas();
-            GlobalConfiguration.Configure(WebApiConfig.Register);
-            RouteConfig.RegisterRoutes(RouteTable.Routes);
-            BundleConfig.RegisterBundles(BundleTable.Bundles);
-
-            // Legacy logging via Application state
-            Application["StartupTime"] = DateTime.Now;
-            Application["RequestCount"] = 0;
-        }
-
-        protected void Application_BeginRequest(object sender, EventArgs e)
-        {
-            // Legacy request tracking via HttpContext.Current
-            HttpContext.Current.Items["RequestStartTime"] = DateTime.Now;
-
-            // Increment global request counter
-            Application.Lock();
-            Application["RequestCount"] = (int)Application["RequestCount"] + 1;
-            Application.UnLock();
-        }
-
-        protected void Application_EndRequest(object sender, EventArgs e)
-        {
-            var startTime = (DateTime)HttpContext.Current.Items["RequestStartTime"];
-            var elapsed = DateTime.Now - startTime;
-
-            // Legacy performance logging
-            if (elapsed.TotalMilliseconds > 500)
-            {
-                System.Diagnostics.Debug.WriteLine(
-                    $"[SLOW REQUEST] {HttpContext.Current.Request.Url} took {elapsed.TotalMilliseconds}ms");
-            }
-        }
-
-        protected void Application_Error(object sender, EventArgs e)
-        {
-            Exception ex = Server.GetLastError();
-
-            // Legacy error handling via HttpContext
-            HttpContext.Current.Response.Clear();
-            HttpContext.Current.Response.StatusCode = 500;
-
-            Server.ClearError();
-            Response.Redirect("~/Error.aspx");
-        }
-
-        protected void Session_Start(object sender, EventArgs e)
-        {
-            Session["SessionStartTime"] = DateTime.Now;
-            Session["IsAuthenticated"] = false;
+            _logger.LogWarning("[SLOW REQUEST] {Path} took {Elapsed}ms",
+                context.Request.Path, stopwatch.ElapsedMilliseconds);
         }
     }
 }
```

---
### File: `Global.asax`
**Summary**: Legacy .NET component 'Global.asax' requiring upgrade to .NET 8.  
**Migration Plan**: 1. Update target framework to net8.0 in .csproj.
2. Replace legacy assembly references with modern NuGet packages.
3. Update namespace imports for .NET 8 compatibility.  
**AI Confidence**: `80.0%`  

**Git Diff Summary**:
```diff
--- a/Global.asax
+++ b/Global.asax
@@ -1 +1,5 @@
-<%@ Application Codebehind="Global.asax.cs" Inherits="LegacyApp.MvcApplication" Language="C#" %>
+<Project Sdk="Microsoft.NET.Sdk.Web">
+  <PropertyGroup>
+    <TargetFramework>net8.0</TargetFramework>
+  </PropertyGroup>
+</Project>
```

---
### File: `Default.aspx`
**Summary**: WebForms page 'Default.aspx' using server controls (GridView, UpdatePanel, ScriptManager), ViewState for state management, and ASPX markup with code-behind pattern.  
**Migration Plan**: 1. Replace .aspx markup with a Blazor component (.razor) or Razor Page.
2. Replace <asp:GridView> with a Blazor table component or MudBlazor DataGrid.
3. Replace <asp:UpdatePanel> with Blazor's built-in re-rendering.
4. Remove ViewState — use Blazor component state (@code { }) instead.
5. Replace code-behind event handlers (Page_Load, Button_Click) with Blazor lifecycle methods.  
**AI Confidence**: `72.0%`  

**Git Diff Summary**:
```diff
--- a/Default.aspx
+++ b/Default.aspx
@@ -1,55 +1,71 @@
-<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Default.aspx.cs" Inherits="LegacyApp.Default" %>
+@page "/"
+@using LegacyApp.Data
+@inject IOrderService OrderService
+@inject IHttpContextAccessor HttpContextAccessor
 
-<!DOCTYPE html>
-<html xmlns="http://www.w3.org/1999/xhtml">
-<head runat="server">
-    <title>Legacy App - Dashboard</title>
-    <link href="~/Content/Site.css" rel="stylesheet" type="text/css" />
-</head>
-<body>
-    <form id="form1" runat="server">
-        <asp:ScriptManager ID="ScriptManager1" runat="server" />
-        
-        <div class="container">
-            <h1>Enterprise Dashboard</h1>
-            
-            <asp:UpdatePanel ID="UpdatePanel1" runat="server">
-                <ContentTemplate>
-                    <asp:GridView ID="OrdersGrid" runat="server" 
-                        AutoGenerateColumns="False"
-                        CssClass="table table-striped"
-                        DataKeyNames="OrderId"
-                        OnRowCommand="OrdersGrid_RowCommand"
-                        AllowPaging="True"
-                        PageSize="25"
-                        OnPageIndexChanging="OrdersGrid_PageIndexChanging">
-                        <Columns>
-                            <asp:BoundField DataField="OrderId" HeaderText="Order #" />
-                            <asp:BoundField DataField="CustomerName" HeaderText="Customer" />
-                            <asp:BoundField DataField="OrderDate" HeaderText="Date" DataFormatString="{0:MM/dd/yyyy}" />
-                            <asp:BoundField DataField="TotalAmount" HeaderText="Total" DataFormatString="{0:C}" />
-                            <asp:TemplateField HeaderText="Status">
-                                <ItemTemplate>
-                                    <asp:Label ID="StatusLabel" runat="server" 
-                                        Text='<%# Eval("Status") %>'
-                                        CssClass='<%# GetStatusCssClass(Eval("Status").ToString()) %>' />
-                                </ItemTemplate>
-                            </asp:TemplateField>
-                            <asp:ButtonField ButtonType="Button" Text="View" CommandName="ViewOrder" />
-                        </Columns>
-                    </asp:GridView>
-                    
-                    <asp:Label ID="lblTotalOrders" runat="server" CssClass="summary-label" />
-                    <asp:Label ID="lblTotalRevenue" runat="server" CssClass="summary-label" />
-                </ContentTemplate>
-                <Triggers>
-                    <asp:AsyncPostBackTrigger ControlID="btnRefresh" EventName="Click" />
-                </Triggers>
-            </asp:UpdatePanel>
-            
-            <asp:Button ID="btnRefresh" runat="server" Text="Refresh Data" OnClick="btnRefresh_Click" CssClass="btn btn-primary" />
-            <asp:Button ID="btnExport" runat="server" Text="Export to Excel" OnClick="btnExport_Click" CssClass="btn btn-success" />
-        </div>
-    </form>
-</body>
-</html>
+<PageTitle>Enterprise Dashboard</PageTitle>
+
+<div class="container">
+    <h1>Enterprise Dashboard</h1>
+
+    <MudTable Items="@orders" Hover="true" Striped="true" Loading="@isLoading"
+              Pagination="new MudTablePager { PageSizeOptions = new[] { 10, 25, 50 } }">
+        <HeaderContent>
+            <MudTh>Order #</MudTh>
+            <MudTh>Customer</MudTh>
+            <MudTh>Date</MudTh>
+            <MudTh>Total</MudTh>
+            <MudTh>Status</MudTh>
+            <MudTh>Actions</MudTh>
+        </HeaderContent>
+        <RowTemplate>
+            <MudTd>@context.OrderId</MudTd>
+            <MudTd>@context.CustomerName</MudTd>
+            <MudTd>@context.OrderDate.ToString("MM/dd/yyyy")</MudTd>
+            <MudTd>@context.TotalAmount.ToString("C")</MudTd>
+            <MudTd><MudChip Color="@GetStatusColor(context.Status)">@context.Status</MudChip></MudTd>
+            <MudTd><MudButton Variant="Variant.Text" OnClick="() => ViewOrder(context.OrderId)">View</MudButton></MudTd>
+        </RowTemplate>
+    </MudTable>
+
+    <div class="mt-4">
+        <MudText Typo="Typo.body1">Total Orders: @totalOrders</MudText>
+        <MudText Typo="Typo.body1">Revenue: @totalRevenue.ToString("C")</MudText>
+    </div>
+
+    <MudButton Variant="Variant.Filled" Color="Color.Primary" OnClick="RefreshData">Refresh</MudButton>
+</div>
+
+@code {
+    private List<OrderDto> orders = new();
+    private bool isLoading = true;
+    private int totalOrders;
+    private decimal totalRevenue;
+
+    protected override async Task OnInitializedAsync()
+    {
+        await RefreshData();
+    }
+
+    private async Task RefreshData()
+    {
+        isLoading = true;
+        orders = await OrderService.GetAllOrdersAsync();
+        totalOrders = orders.Count;
+        totalRevenue = orders.Where(o => o.Status == "Completed").Sum(o => o.TotalAmount);
+        isLoading = false;
+    }
+
+    private void ViewOrder(int orderId)
+    {
+        NavigationManager.NavigateTo($"/orders/{orderId}");
+    }
+
+    private Color GetStatusColor(string status) => status switch
+    {
+        "Completed" => Color.Success,
+        "Pending" => Color.Warning,
+        "Cancelled" => Color.Error,
+        _ => Color.Default
+    };
+}
```

---
### File: `Web.config`
**Summary**: XML configuration file 'Web.config' containing connection strings, system.web settings, system.serviceModel WCF bindings, Entity Framework configuration, and custom HTTP modules.  
**Migration Plan**: 1. Move <connectionStrings> to appsettings.json under "ConnectionStrings" key.
2. Move <appSettings> to appsettings.json.
3. Replace <system.web> authentication/authorization with ASP.NET Core Identity middleware.
4. Replace <system.serviceModel> WCF config with code-based endpoint registration.
5. Replace <entityFramework> config with EF Core registration in Program.cs.
6. Replace <httpModules> with ASP.NET Core middleware in Program.cs.  
**AI Confidence**: `88.0%`  

**Git Diff Summary**:
```diff
--- a/Web.config
+++ b/Web.config
@@ -1,87 +1,35 @@
-<?xml version="1.0" encoding="utf-8"?>
-<configuration>
-  <configSections>
-    <section name="entityFramework" type="System.Data.Entity.Internal.ConfigFile.EntityFrameworkSection, EntityFramework, Version=6.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089" requirePermission="false" />
-  </configSections>
+{
+  "ConnectionStrings": {
+    "DefaultConnection": "Server=.\\SQLEXPRESS;Database=LegacyAppDB;Trusted_Connection=true;TrustServerCertificate=true",
+    "ReportingDB": "Server=.\\SQLEXPRESS;Database=ReportingDB;Trusted_Connection=true;TrustServerCertificate=true"
+  },
+  "AppSettings": {
+    "MaxPageSize": 100,
+    "EnableAuditLog": true,
+    "SmtpServer": "smtp.company.internal"
+  },
+  "Logging": {
+    "LogLevel": {
+      "Default": "Information",
+      "Microsoft.AspNetCore": "Warning"
+    }
+  }
+}
 
-  <connectionStrings>
-    <add name="DefaultConnection" connectionString="Data Source=.\SQLEXPRESS;Initial Catalog=LegacyAppDB;Integrated Security=True" providerName="System.Data.SqlClient" />
-    <add name="ReportingDB" connectionString="Data Source=.\SQLEXPRESS;Initial Catalog=ReportingDB;Integrated Security=True" providerName="System.Data.SqlClient" />
-  </connectionStrings>
-
-  <appSettings>
-    <add key="MaxPageSize" value="100" />
-    <add key="EnableAuditLog" value="true" />
-    <add key="SmtpServer" value="smtp.company.internal" />
-    <add key="webpages:Version" value="3.0.0.0" />
-    <add key="webpages:Enabled" value="false" />
-    <add key="ClientValidationEnabled" value="true" />
-    <add key="UnobtrusiveJavaScriptEnabled" value="true" />
-  </appSettings>
-
-  <system.web>
-    <compilation debug="true" targetFramework="4.7.2">
-      <assemblies>
-        <add assembly="System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31BF3856AD364E35" />
-      </assemblies>
-    </compilation>
-    <httpRuntime targetFramework="4.7.2" maxRequestLength="32768" />
-    <authentication mode="Forms">
-      <forms loginUrl="~/Login.aspx" timeout="2880" />
-    </authentication>
-    <authorization>
-      <deny users="?" />
-    </authorization>
-    <customErrors mode="RemoteOnly" defaultRedirect="~/Error.aspx">
-      <error statusCode="404" redirect="~/NotFound.aspx" />
-    </customErrors>
-    <sessionState mode="InProc" timeout="20" />
-    <pages>
-      <namespaces>
-        <add namespace="System.Web.Optimization" />
-      </namespaces>
-    </pages>
-    <httpModules>
-      <add name="AuditModule" type="LegacyApp.Modules.AuditHttpModule, LegacyApp" />
-    </httpModules>
-  </system.web>
-
-  <system.serviceModel>
-    <services>
-      <service name="LegacyApp.Services.OrderService" behaviorConfiguration="ServiceBehavior">
-        <endpoint address="" binding="basicHttpBinding" contract="LegacyApp.Services.IOrderService" />
-        <endpoint address="mex" binding="mexHttpBinding" contract="IMetadataExchange" />
-      </service>
-    </services>
-    <behaviors>
-      <serviceBehaviors>
-        <behavior name="ServiceBehavior">
-          <serviceMetadata httpGetEnabled="true" />
-          <serviceDebug includeExceptionDetailInFaults="false" />
-        </behavior>
-      </serviceBehaviors>
-    </behaviors>
-    <bindings>
-      <basicHttpBinding>
-        <binding maxReceivedMessageSize="2147483647" maxBufferSize="2147483647">
-          <readerQuotas maxStringContentLength="2147483647" maxArrayLength="2147483647" />
-        </binding>
-      </basicHttpBinding>
-    </bindings>
-  </system.serviceModel>
-
-  <entityFramework>
-    <defaultConnectionFactory type="System.Data.Entity.Infrastructure.SqlConnectionFactory, EntityFramework" />
-    <providers>
-      <provider invariantName="System.Data.SqlClient" type="System.Data.Entity.SqlServer.SqlProviderServices, EntityFramework.SqlServer" />
-    </providers>
-  </entityFramework>
-
-  <system.webServer>
-    <modules runAllManagedModulesForAllRequests="true" />
-    <handlers>
-      <remove name="ExtensionlessUrlHandler-Integrated-4.0" />
-      <add name="ExtensionlessUrlHandler-Integrated-4.0" path="*." verb="*" type="System.Web.Handlers.TransferRequestHandler" preCondition="integratedMode,runtimeVersionv4.0" />
-    </handlers>
-  </system.webServer>
-</configuration>
+// Program.cs — replaces Web.config system sections:
+// var builder = WebApplication.CreateBuilder(args);
+//
+// // Replaces <system.web><authentication mode="Forms">
+// builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
+//     .AddCookie(options => { options.LoginPath = "/login"; options.ExpireTimeSpan = TimeSpan.FromDays(2); });
+//
+// // Replaces <system.web><sessionState>
+// builder.Services.AddDistributedMemoryCache();
+// builder.Services.AddSession(options => { options.IdleTimeout = TimeSpan.FromMinutes(20); });
+//
+// // Replaces <entityFramework>
+// builder.Services.AddDbContext<AppDbContext>(o =>
+//     o.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
+//
+// // Replaces <httpModules><add name="AuditModule">
+// app.UseMiddleware<AuditMiddleware>();
```

---
### File: `Controllers\HomeController.cs`
**Summary**: Legacy ASP.NET MVC controller or HTTP module 'HomeController.cs' using HttpContext.Current, Session, Application state, Cache API, and ConfigurationManager.  
**Migration Plan**: 1. Replace HttpContext.Current with constructor-injected IHttpContextAccessor.
2. Replace System.Web.Mvc.Controller with Microsoft.AspNetCore.Mvc.Controller.
3. Replace ConfigurationManager with IConfiguration.
4. Replace ASP.NET Cache with IMemoryCache or IDistributedCache.
5. Replace Session direct access with HttpContext.Session extension methods.
6. Replace Application state with a singleton service registered in DI.  
**AI Confidence**: `85.0%`  

**Git Diff Summary**:
```diff
--- a/Controllers\HomeController.cs
+++ b/Controllers\HomeController.cs
@@ -1,118 +1,90 @@
-using System;
-using System.Collections.Generic;
-using System.Linq;
-using System.Web;
-using System.Web.Mvc;
-using System.Web.Caching;
-using System.Configuration;
-using System.Data.SqlClient;
+using Microsoft.AspNetCore.Mvc;
+using Microsoft.AspNetCore.Http;
+using Microsoft.Extensions.Caching.Memory;
+using Microsoft.Extensions.Configuration;
+using Microsoft.EntityFrameworkCore;
 
-namespace LegacyApp.Controllers
+namespace LegacyApp.Controllers;
+
+/// <summary>Home controller migrated to ASP.NET Core with dependency injection.</summary>
+public class HomeController : Controller
 {
-    public class HomeController : Controller
+    private readonly IHttpContextAccessor _httpContextAccessor;
+    private readonly IMemoryCache _cache;
+    private readonly IConfiguration _configuration;
+    private readonly AppDbContext _db;
+
+    public HomeController(
+        IHttpContextAccessor httpContextAccessor,
+        IMemoryCache cache,
+        IConfiguration configuration,
+        AppDbContext db)
     {
-        // Legacy: using HttpContext.Current instead of DI
-        public ActionResult Index()
+        _httpContextAccessor = httpContextAccessor;
+        _cache = cache;
+        _configuration = configuration;
+        _db = db;
+    }
+
+    public async Task<IActionResult> Index()
+    {
+        // Replaces HttpContext.Current.User.Identity.Name
+        var userName = _httpContextAccessor.HttpContext?.User?.Identity?.Name ?? "Anonymous";
+        ViewBag.UserName = userName;
+        ViewBag.ServerTime = DateTime.UtcNow;
+
+        // Replaces HttpContext.Current.Cache with IMemoryCache
+        if (!_cache.TryGetValue("DashboardStats", out Dictionary<string, object>? stats))
         {
-            // Access user via HttpContext.Current
-            var userName = HttpContext.Current.User.Identity.Name;
-            ViewBag.UserName = userName;
-            ViewBag.ServerTime = DateTime.Now;
+            stats = await LoadDashboardStatsAsync();
+            _cache.Set("DashboardStats", stats, TimeSpan.FromMinutes(5));
+        }
+        ViewBag.Stats = stats;
 
-            // Legacy: using ASP.NET Cache directly
-            var cachedData = HttpContext.Current.Cache["DashboardStats"];
-            if (cachedData == null)
+        return View();
+    }
+
+    [HttpPost]
+    [ValidateAntiForgeryToken]
+    public async Task<IActionResult> UpdateProfile(string email, string phone)
+    {
+        var userId = Request.Cookies["UserId"];
+        if (string.IsNullOrEmpty(userId))
+            return Unauthorized("Not authenticated");
+
+        var user = await _db.Users.FindAsync(int.Parse(userId));
+        if (user is null) return NotFound();
+
+        user.Email = email;
+        user.Phone = phone;
+        await _db.SaveChangesAsync();
+
+        Response.Cookies.Append("LastUpdate", DateTime.UtcNow.ToString(), new CookieOptions
+        {
+            Expires = DateTimeOffset.UtcNow.AddDays(30)
+        });
+
+        TempData["Message"] = "Profile updated successfully.";
+        return RedirectToAction("Index");
+    }
+
+    private async Task<Dictionary<string, object>> LoadDashboardStatsAsync()
+    {
+        var stats = await _db.Orders
+            .GroupBy(_ => 1)
+            .Select(g => new
             {
-                var stats = LoadDashboardStats();
-                HttpContext.Current.Cache.Insert(
-                    "DashboardStats",
-                    stats,
-                    null,
-                    DateTime.Now.AddMinutes(5),
-                    Cache.NoSlidingExpiration);
-                cachedData = stats;
-            }
+                TotalOrders = g.Count(),
+                TotalCustomers = g.Select(o => o.CustomerId).Distinct().Count(),
+                Revenue = g.Where(o => o.Status == "Completed").Sum(o => o.TotalAmount)
+            })
+            .FirstOrDefaultAsync();
 
-            ViewBag.Stats = cachedData;
-
-            // Legacy: using Session directly
-            Session["LastVisited"] = "Home/Index";
-            Session["VisitCount"] = (int)(Session["VisitCount"] ?? 0) + 1;
-
-            // Legacy: using Application state
-            HttpContext.Current.Application.Lock();
-            HttpContext.Current.Application["TotalPageViews"] =
-                (int)(HttpContext.Current.Application["TotalPageViews"] ?? 0) + 1;
-            HttpContext.Current.Application.UnLock();
-
-            return View();
-        }
-
-        [HttpPost]
-        [ValidateAntiForgeryToken]
-        public ActionResult UpdateProfile(string email, string phone)
+        return new Dictionary<string, object>
         {
-            // Legacy: reading from Request directly
-            var userId = HttpContext.Current.Request.Cookies["UserId"]?.Value;
-
-            if (string.IsNullOrEmpty(userId))
-            {
-                return new HttpStatusCodeResult(401, "Not authenticated");
-            }
-
-            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
-            using (var conn = new SqlConnection(connStr))
-            {
-                conn.Open();
-                var cmd = new SqlCommand(
-                    "UPDATE Users SET Email = @Email, Phone = @Phone WHERE UserId = @UserId", conn);
-                cmd.Parameters.AddWithValue("@Email", email);
-                cmd.Parameters.AddWithValue("@Phone", phone);
-                cmd.Parameters.AddWithValue("@UserId", userId);
-                cmd.ExecuteNonQuery();
-            }
-
-            // Legacy: writing response cookies
-            var cookie = new HttpCookie("LastUpdate", DateTime.Now.ToString());
-            cookie.Expires = DateTime.Now.AddDays(30);
-            HttpContext.Current.Response.Cookies.Add(cookie);
-
-            TempData["Message"] = "Profile updated successfully.";
-            return RedirectToAction("Index");
-        }
-
-        public ActionResult About()
-        {
-            ViewBag.Message = "Legacy ASP.NET MVC Application";
-            ViewBag.Framework = "NET Framework 4.7.2";
-            ViewBag.ServerInfo = HttpContext.Current.Server.MapPath("~/");
-            return View();
-        }
-
-        private Dictionary<string, object> LoadDashboardStats()
-        {
-            var stats = new Dictionary<string, object>();
-            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
-            using (var conn = new SqlConnection(connStr))
-            {
-                conn.Open();
-                var cmd = new SqlCommand(
-                    @"SELECT 
-                        (SELECT COUNT(*) FROM Orders) AS TotalOrders,
-                        (SELECT COUNT(*) FROM Customers) AS TotalCustomers,
-                        (SELECT SUM(TotalAmount) FROM Orders WHERE Status = 'Completed') AS Revenue",
-                    conn);
-                using (var reader = cmd.ExecuteReader())
-                {
-                    if (reader.Read())
-                    {
-                        stats["TotalOrders"] = reader["TotalOrders"];
-                        stats["TotalCustomers"] = reader["TotalCustomers"];
-                        stats["Revenue"] = reader["Revenue"];
-                    }
-                }
-            }
-            return stats;
-        }
+            ["TotalOrders"] = stats?.TotalOrders ?? 0,
+            ["TotalCustomers"] = stats?.TotalCustomers ?? 0,
+            ["Revenue"] = stats?.Revenue ?? 0m
+        };
     }
 }
```

---
### File: `Services\OrderService.svc`
**Summary**: WCF service host file 'OrderService.svc' that routes SOAP requests to the service implementation. This file defines the ServiceHost directive used by IIS to activate the WCF service.  
**Migration Plan**: 1. Remove the .svc file entirely — .NET 8 does not use .svc hosting.
2. Register the service as a Minimal API endpoint in Program.cs.
3. If SOAP compatibility is required, use CoreWCF NuGet package.
4. For new clients, prefer gRPC with Protobuf contracts.  
**AI Confidence**: `80.0%`  

**Git Diff Summary**:
```diff
--- a/Services\OrderService.svc
+++ b/Services\OrderService.svc
@@ -1 +1,11 @@
-<%@ ServiceHost Language="C#" Debug="true" Service="LegacyApp.Services.OrderService" CodeBehind="OrderService.svc.cs" %>
+// .svc file is eliminated in .NET 8.
+// Service is registered in Program.cs as a Minimal API:
+
+// Program.cs
+var builder = WebApplication.CreateBuilder(args);
+builder.Services.AddDbContext<AppDbContext>(o =>
+    o.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
+
+var app = builder.Build();
+app.MapGroup("/api/orderservices").MapOrderServiceEndpoints();
+app.Run();
```

---
### File: `Services\OrderService.svc.cs`
**Summary**: WCF service implementation 'OrderService.svc.cs' with [ServiceContract] and [OperationContract] attributes, using ADO.NET for data access via SqlConnection and ConfigurationManager.  
**Migration Plan**: 1. Replace [ServiceContract] interface with ASP.NET Core Minimal API endpoint group.
2. Replace [OperationContract] methods with MapGet/MapPost/MapPut/MapDelete handlers.
3. Replace [DataContract]/[DataMember] DTOs with C# records.
4. Replace ConfigurationManager with IConfiguration via dependency injection.
5. Replace raw SqlConnection/SqlCommand with Entity Framework Core DbContext.
6. Add proper input validation with FluentValidation or Data Annotations.  
**AI Confidence**: `78.0%`  

**Git Diff Summary**:
```diff
--- a/Services\OrderService.svc.cs
+++ b/Services\OrderService.svc.cs
@@ -1,197 +1,90 @@
-using System;
-using System.Collections.Generic;
-using System.Data;
-using System.Data.SqlClient;
-using System.Configuration;
-using System.ServiceModel;
-using System.ServiceModel.Activation;
-using System.Runtime.Serialization;
+using Microsoft.AspNetCore.Http.HttpResults;
+using Microsoft.EntityFrameworkCore;
 
-namespace LegacyApp.Services
+namespace LegacyApp.Endpoints;
+
+/// <summary>Order data transfer object.</summary>
+public record OrderDto(int OrderId, string CustomerName, DateTime OrderDate, decimal TotalAmount, string Status);
+
+/// <summary>Request payload for creating a new order.</summary>
+public record CreateOrderRequest(int CustomerId, List<OrderItemRequest> Items);
+public record OrderItemRequest(int ProductId, int Quantity, decimal UnitPrice);
+
+/// <summary>Standard API response envelope.</summary>
+public record ServiceResponse(bool Success, string Message, int? OrderId = null);
+
+/// <summary>Minimal API endpoints replacing the WCF OrderService.</summary>
+public static class OrderEndpoints
 {
-    [DataContract]
-    public class OrderDto
+    public static RouteGroupBuilder MapOrderEndpoints(this RouteGroupBuilder group)
     {
-        [DataMember] public int OrderId { get; set; }
-        [DataMember] public string CustomerName { get; set; }
-        [DataMember] public DateTime OrderDate { get; set; }
-        [DataMember] public decimal TotalAmount { get; set; }
-        [DataMember] public string Status { get; set; }
+        group.MapGet("/", GetAllOrders).WithName("GetOrders").WithOpenApi();
+        group.MapGet("/{id:int}", GetOrderById).WithName("GetOrder").WithOpenApi();
+        group.MapPost("/", CreateOrder).WithName("CreateOrder").WithOpenApi();
+        group.MapPut("/{id:int}/status", UpdateStatus).WithName("UpdateOrderStatus").WithOpenApi();
+        group.MapDelete("/{id:int}", CancelOrder).WithName("CancelOrder").WithOpenApi();
+        return group;
     }
 
-    [DataContract]
-    public class OrderCreateRequest
+    private static async Task<Ok<List<OrderDto>>> GetAllOrders(AppDbContext db)
     {
-        [DataMember] public int CustomerId { get; set; }
-        [DataMember] public List<OrderItemRequest> Items { get; set; }
+        var orders = await db.Orders
+            .Include(o => o.Customer)
+            .OrderByDescending(o => o.OrderDate)
+            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
+            .ToListAsync();
+        return TypedResults.Ok(orders);
     }
 
-    [DataContract]
-    public class OrderItemRequest
+    private static async Task<Results<Ok<OrderDto>, NotFound>> GetOrderById(int id, AppDbContext db)
     {
-        [DataMember] public int ProductId { get; set; }
-        [DataMember] public int Quantity { get; set; }
-        [DataMember] public decimal UnitPrice { get; set; }
+        var order = await db.Orders.Include(o => o.Customer)
+            .Where(o => o.OrderId == id)
+            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
+            .FirstOrDefaultAsync();
+        return order is not null ? TypedResults.Ok(order) : TypedResults.NotFound();
     }
 
-    [DataContract]
-    public class ServiceResponse
+    private static async Task<Created<ServiceResponse>> CreateOrder(CreateOrderRequest req, AppDbContext db)
     {
-        [DataMember] public bool Success { get; set; }
-        [DataMember] public string Message { get; set; }
-        [DataMember] public int? OrderId { get; set; }
+        var total = req.Items.Sum(i => i.Quantity * i.UnitPrice);
+        var order = new Order
+        {
+            CustomerId = req.CustomerId,
+            OrderDate = DateTime.UtcNow,
+            TotalAmount = total,
+            Status = "Pending",
+            Items = req.Items.Select(i => new OrderItem
+            {
+                ProductId = i.ProductId,
+                Quantity = i.Quantity,
+                UnitPrice = i.UnitPrice
+            }).ToList()
+        };
+
+        db.Orders.Add(order);
+        await db.SaveChangesAsync();
+
+        return TypedResults.Created($"/api/orders/{order.OrderId}",
+            new ServiceResponse(true, "Order created.", order.OrderId));
     }
 
-    [ServiceContract]
-    public interface IOrderService
+    private static async Task<Results<Ok<ServiceResponse>, NotFound>> UpdateStatus(
+        int id, string newStatus, AppDbContext db)
     {
-        [OperationContract]
-        List<OrderDto> GetAllOrders();
-
-        [OperationContract]
-        OrderDto GetOrderById(int orderId);
-
-        [OperationContract]
-        ServiceResponse CreateOrder(OrderCreateRequest request);
-
-        [OperationContract]
-        ServiceResponse UpdateOrderStatus(int orderId, string newStatus);
-
-        [OperationContract]
-        ServiceResponse CancelOrder(int orderId);
+        var order = await db.Orders.FindAsync(id);
+        if (order is null) return TypedResults.NotFound();
+        order.Status = newStatus;
+        await db.SaveChangesAsync();
+        return TypedResults.Ok(new ServiceResponse(true, "Status updated."));
     }
 
-    [AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Allowed)]
-    public class OrderService : IOrderService
+    private static async Task<Results<Ok<ServiceResponse>, NotFound>> CancelOrder(int id, AppDbContext db)
     {
-        private string ConnectionString =>
-            ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
-
-        public List<OrderDto> GetAllOrders()
-        {
-            var orders = new List<OrderDto>();
-            using (var conn = new SqlConnection(ConnectionString))
-            {
-                conn.Open();
-                var cmd = new SqlCommand(
-                    @"SELECT o.OrderId, c.CustomerName, o.OrderDate, o.TotalAmount, o.Status
-                      FROM Orders o INNER JOIN Customers c ON o.CustomerId = c.CustomerId
-                      ORDER BY o.OrderDate DESC", conn);
-
-                using (var reader = cmd.ExecuteReader())
-                {
-                    while (reader.Read())
-                    {
-                        orders.Add(new OrderDto
-                        {
-                            OrderId = reader.GetInt32(0),
-                            CustomerName = reader.GetString(1),
-                            OrderDate = reader.GetDateTime(2),
-                            TotalAmount = reader.GetDecimal(3),
-                            Status = reader.GetString(4)
-                        });
-                    }
-                }
-            }
-            return orders;
-        }
-
-        public OrderDto GetOrderById(int orderId)
-        {
-            using (var conn = new SqlConnection(ConnectionString))
-            {
-                conn.Open();
-                var cmd = new SqlCommand(
-                    @"SELECT o.OrderId, c.CustomerName, o.OrderDate, o.TotalAmount, o.Status
-                      FROM Orders o INNER JOIN Customers c ON o.CustomerId = c.CustomerId
-                      WHERE o.OrderId = @OrderId", conn);
-                cmd.Parameters.AddWithValue("@OrderId", orderId);
-
-                using (var reader = cmd.ExecuteReader())
-                {
-                    if (reader.Read())
-                    {
-                        return new OrderDto
-                        {
-                            OrderId = reader.GetInt32(0),
-                            CustomerName = reader.GetString(1),
-                            OrderDate = reader.GetDateTime(2),
-                            TotalAmount = reader.GetDecimal(3),
-                            Status = reader.GetString(4)
-                        };
-                    }
-                }
-            }
-            return null;
-        }
-
-        public ServiceResponse CreateOrder(OrderCreateRequest request)
-        {
-            try
-            {
-                using (var conn = new SqlConnection(ConnectionString))
-                {
-                    conn.Open();
-                    using (var transaction = conn.BeginTransaction())
-                    {
-                        var cmd = new SqlCommand(
-                            @"INSERT INTO Orders (CustomerId, OrderDate, TotalAmount, Status) 
-                              VALUES (@CustomerId, @OrderDate, @Total, 'Pending');
-                              SELECT SCOPE_IDENTITY();", conn, transaction);
-
-                        decimal total = 0;
-                        foreach (var item in request.Items)
-                            total += item.Quantity * item.UnitPrice;
-
-                        cmd.Parameters.AddWithValue("@CustomerId", request.CustomerId);
-                        cmd.Parameters.AddWithValue("@OrderDate", DateTime.Now);
-                        cmd.Parameters.AddWithValue("@Total", total);
-
-                        int orderId = Convert.ToInt32(cmd.ExecuteScalar());
-
-                        foreach (var item in request.Items)
-                        {
-                            var itemCmd = new SqlCommand(
-                                @"INSERT INTO OrderItems (OrderId, ProductId, Quantity, UnitPrice)
-                                  VALUES (@OrderId, @ProductId, @Qty, @Price)", conn, transaction);
-                            itemCmd.Parameters.AddWithValue("@OrderId", orderId);
-                            itemCmd.Parameters.AddWithValue("@ProductId", item.ProductId);
-                            itemCmd.Parameters.AddWithValue("@Qty", item.Quantity);
-                            itemCmd.Parameters.AddWithValue("@Price", item.UnitPrice);
-                            itemCmd.ExecuteNonQuery();
-                        }
-
-                        transaction.Commit();
-                        return new ServiceResponse { Success = true, Message = "Order created.", OrderId = orderId };
-                    }
-                }
-            }
-            catch (Exception ex)
-            {
-                return new ServiceResponse { Success = false, Message = ex.Message };
-            }
-        }
-
-        public ServiceResponse UpdateOrderStatus(int orderId, string newStatus)
-        {
-            using (var conn = new SqlConnection(ConnectionString))
-            {
-                conn.Open();
-                var cmd = new SqlCommand("UPDATE Orders SET Status = @Status WHERE OrderId = @Id", conn);
-                cmd.Parameters.AddWithValue("@Status", newStatus);
-                cmd.Parameters.AddWithValue("@Id", orderId);
-                int affected = cmd.ExecuteNonQuery();
-                return new ServiceResponse
-                {
-                    Success = affected > 0,
-                    Message = affected > 0 ? "Status updated." : "Order not found."
-                };
-            }
-        }
-
-        public ServiceResponse CancelOrder(int orderId)
-        {
-            return UpdateOrderStatus(orderId, "Cancelled");
-        }
+        var order = await db.Orders.FindAsync(id);
+        if (order is null) return TypedResults.NotFound();
+        order.Status = "Cancelled";
+        await db.SaveChangesAsync();
+        return TypedResults.Ok(new ServiceResponse(true, "Order cancelled."));
     }
 }
```

---