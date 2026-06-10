using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.Caching;
using System.Configuration;
using System.Data.SqlClient;

namespace LegacyApp.Controllers
{
    public class HomeController : Controller
    {
        // Legacy: using HttpContext.Current instead of DI
        public ActionResult Index()
        {
            // Access user via HttpContext.Current
            var userName = HttpContext.Current.User.Identity.Name;
            ViewBag.UserName = userName;
            ViewBag.ServerTime = DateTime.Now;

            // Legacy: using ASP.NET Cache directly
            var cachedData = HttpContext.Current.Cache["DashboardStats"];
            if (cachedData == null)
            {
                var stats = LoadDashboardStats();
                HttpContext.Current.Cache.Insert(
                    "DashboardStats",
                    stats,
                    null,
                    DateTime.Now.AddMinutes(5),
                    Cache.NoSlidingExpiration);
                cachedData = stats;
            }

            ViewBag.Stats = cachedData;

            // Legacy: using Session directly
            Session["LastVisited"] = "Home/Index";
            Session["VisitCount"] = (int)(Session["VisitCount"] ?? 0) + 1;

            // Legacy: using Application state
            HttpContext.Current.Application.Lock();
            HttpContext.Current.Application["TotalPageViews"] =
                (int)(HttpContext.Current.Application["TotalPageViews"] ?? 0) + 1;
            HttpContext.Current.Application.UnLock();

            return View();
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult UpdateProfile(string email, string phone)
        {
            // Legacy: reading from Request directly
            var userId = HttpContext.Current.Request.Cookies["UserId"]?.Value;

            if (string.IsNullOrEmpty(userId))
            {
                return new HttpStatusCodeResult(401, "Not authenticated");
            }

            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
            using (var conn = new SqlConnection(connStr))
            {
                conn.Open();
                var cmd = new SqlCommand(
                    "UPDATE Users SET Email = @Email, Phone = @Phone WHERE UserId = @UserId", conn);
                cmd.Parameters.AddWithValue("@Email", email);
                cmd.Parameters.AddWithValue("@Phone", phone);
                cmd.Parameters.AddWithValue("@UserId", userId);
                cmd.ExecuteNonQuery();
            }

            // Legacy: writing response cookies
            var cookie = new HttpCookie("LastUpdate", DateTime.Now.ToString());
            cookie.Expires = DateTime.Now.AddDays(30);
            HttpContext.Current.Response.Cookies.Add(cookie);

            TempData["Message"] = "Profile updated successfully.";
            return RedirectToAction("Index");
        }

        public ActionResult About()
        {
            ViewBag.Message = "Legacy ASP.NET MVC Application";
            ViewBag.Framework = "NET Framework 4.7.2";
            ViewBag.ServerInfo = HttpContext.Current.Server.MapPath("~/");
            return View();
        }

        private Dictionary<string, object> LoadDashboardStats()
        {
            var stats = new Dictionary<string, object>();
            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
            using (var conn = new SqlConnection(connStr))
            {
                conn.Open();
                var cmd = new SqlCommand(
                    @"SELECT 
                        (SELECT COUNT(*) FROM Orders) AS TotalOrders,
                        (SELECT COUNT(*) FROM Customers) AS TotalCustomers,
                        (SELECT SUM(TotalAmount) FROM Orders WHERE Status = 'Completed') AS Revenue",
                    conn);
                using (var reader = cmd.ExecuteReader())
                {
                    if (reader.Read())
                    {
                        stats["TotalOrders"] = reader["TotalOrders"];
                        stats["TotalCustomers"] = reader["TotalCustomers"];
                        stats["Revenue"] = reader["Revenue"];
                    }
                }
            }
            return stats;
        }
    }
}
