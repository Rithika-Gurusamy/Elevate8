// Program.cs — replaces Global.asax.cs entirely

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
}