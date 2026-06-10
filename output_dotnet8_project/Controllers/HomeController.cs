using Microsoft.AspNetCore.Mvc;
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

    /// <summary>
    /// Initializes a new instance of the <see cref="HomeController"/> class.
    /// </summary>
    /// <param name="httpContextAccessor">The accessor for the current HTTP context.</param>
    /// <param name="cache">The in-memory cache service.</param>
    /// <param name="configuration">The application configuration service.</param>
    /// <param name="db">The application database context.</param>
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

    /// <summary>
    /// Displays the application's home page with dashboard statistics.
    /// </summary>
    /// <returns>An <see cref="IActionResult"/> representing the view.</returns>
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

    /// <summary>
    /// Handles profile update requests, persisting changes to the database.
    /// </summary>
    /// <param name="email">The new email address for the user.</param>
    /// <param name="phone">The new phone number for the user.</param>
    /// <returns>An <see cref="IActionResult"/> redirecting to the Index page upon success, or an error response.</returns>
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

    /// <summary>
    /// Asynchronously loads dashboard statistics from the database.
    /// </summary>
    /// <returns>A dictionary containing dashboard statistics.</returns>
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
}