using System;
using System.Web;
using System.Web.Mvc;
using System.Web.Routing;
using System.Web.Http;
using System.Web.Optimization;

namespace LegacyApp
{
    public class MvcApplication : System.Web.HttpApplication
    {
        protected void Application_Start()
        {
            AreaRegistration.RegisterAllAreas();
            GlobalConfiguration.Configure(WebApiConfig.Register);
            RouteConfig.RegisterRoutes(RouteTable.Routes);
            BundleConfig.RegisterBundles(BundleTable.Bundles);

            // Legacy logging via Application state
            Application["StartupTime"] = DateTime.Now;
            Application["RequestCount"] = 0;
        }

        protected void Application_BeginRequest(object sender, EventArgs e)
        {
            // Legacy request tracking via HttpContext.Current
            HttpContext.Current.Items["RequestStartTime"] = DateTime.Now;

            // Increment global request counter
            Application.Lock();
            Application["RequestCount"] = (int)Application["RequestCount"] + 1;
            Application.UnLock();
        }

        protected void Application_EndRequest(object sender, EventArgs e)
        {
            var startTime = (DateTime)HttpContext.Current.Items["RequestStartTime"];
            var elapsed = DateTime.Now - startTime;

            // Legacy performance logging
            if (elapsed.TotalMilliseconds > 500)
            {
                System.Diagnostics.Debug.WriteLine(
                    $"[SLOW REQUEST] {HttpContext.Current.Request.Url} took {elapsed.TotalMilliseconds}ms");
            }
        }

        protected void Application_Error(object sender, EventArgs e)
        {
            Exception ex = Server.GetLastError();

            // Legacy error handling via HttpContext
            HttpContext.Current.Response.Clear();
            HttpContext.Current.Response.StatusCode = 500;

            Server.ClearError();
            Response.Redirect("~/Error.aspx");
        }

        protected void Session_Start(object sender, EventArgs e)
        {
            Session["SessionStartTime"] = DateTime.Now;
            Session["IsAuthenticated"] = false;
        }
    }
}
