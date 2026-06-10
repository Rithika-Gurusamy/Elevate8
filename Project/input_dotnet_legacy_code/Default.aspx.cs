using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Configuration;
using System.Web;
using System.Web.UI;
using System.Web.UI.WebControls;

namespace LegacyApp
{
    public partial class Default : System.Web.UI.Page
    {
        protected void Page_Load(object sender, EventArgs e)
        {
            if (!IsPostBack)
            {
                // Check authentication via HttpContext
                if (HttpContext.Current.User == null || !HttpContext.Current.User.Identity.IsAuthenticated)
                {
                    Response.Redirect("~/Login.aspx");
                    return;
                }

                // Store user info in ViewState
                ViewState["CurrentUser"] = HttpContext.Current.User.Identity.Name;
                ViewState["LoginTime"] = DateTime.Now;

                // Log page access using Session
                Session["LastPageVisited"] = "Default.aspx";
                Session["PageAccessCount"] = (int)(Session["PageAccessCount"] ?? 0) + 1;

                BindOrdersGrid();
                LoadDashboardSummary();
            }
        }

        private void BindOrdersGrid()
        {
            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
            using (SqlConnection conn = new SqlConnection(connStr))
            {
                conn.Open();
                string query = @"
                    SELECT TOP 100 
                        o.OrderId, c.CustomerName, o.OrderDate, 
                        o.TotalAmount, o.Status
                    FROM Orders o 
                    INNER JOIN Customers c ON o.CustomerId = c.CustomerId
                    ORDER BY o.OrderDate DESC";

                SqlCommand cmd = new SqlCommand(query, conn);
                SqlDataAdapter da = new SqlDataAdapter(cmd);
                DataTable dt = new DataTable();
                da.Fill(dt);

                OrdersGrid.DataSource = dt;
                OrdersGrid.DataBind();
            }
        }

        private void LoadDashboardSummary()
        {
            string connStr = ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;
            using (SqlConnection conn = new SqlConnection(connStr))
            {
                conn.Open();
                SqlCommand cmd = new SqlCommand(
                    "SELECT COUNT(*) AS TotalOrders, SUM(TotalAmount) AS Revenue FROM Orders WHERE YEAR(OrderDate) = YEAR(GETDATE())",
                    conn);
                SqlDataReader reader = cmd.ExecuteReader();
                if (reader.Read())
                {
                    lblTotalOrders.Text = $"Total Orders: {reader["TotalOrders"]}";
                    lblTotalRevenue.Text = $"Revenue: {reader["Revenue"]:C}";
                }
            }
        }

        protected void OrdersGrid_RowCommand(object sender, GridViewCommandEventArgs e)
        {
            if (e.CommandName == "ViewOrder")
            {
                int rowIndex = Convert.ToInt32(e.CommandArgument);
                string orderId = OrdersGrid.DataKeys[rowIndex].Value.ToString();

                // Use HttpContext.Current to store state between pages
                HttpContext.Current.Items["SelectedOrderId"] = orderId;
                Response.Redirect($"~/OrderDetails.aspx?id={orderId}");
            }
        }

        protected void OrdersGrid_PageIndexChanging(object sender, GridViewPageEventArgs e)
        {
            OrdersGrid.PageIndex = e.NewPageIndex;
            BindOrdersGrid();
        }

        protected void btnRefresh_Click(object sender, EventArgs e)
        {
            BindOrdersGrid();
            LoadDashboardSummary();
        }

        protected void btnExport_Click(object sender, EventArgs e)
        {
            // Legacy pattern: writing directly to HttpResponse
            Response.Clear();
            Response.ContentType = "application/vnd.ms-excel";
            Response.AddHeader("Content-Disposition", "attachment; filename=Orders.xls");

            System.IO.StringWriter sw = new System.IO.StringWriter();
            HtmlTextWriter hw = new HtmlTextWriter(sw);
            OrdersGrid.RenderControl(hw);
            Response.Write(sw.ToString());
            Response.End();
        }

        protected string GetStatusCssClass(string status)
        {
            switch (status)
            {
                case "Completed": return "badge badge-success";
                case "Pending": return "badge badge-warning";
                case "Cancelled": return "badge badge-danger";
                default: return "badge badge-secondary";
            }
        }

        public override void VerifyRenderingInServerForm(Control control)
        {
            // Required for Excel export of GridView
        }
    }
}
