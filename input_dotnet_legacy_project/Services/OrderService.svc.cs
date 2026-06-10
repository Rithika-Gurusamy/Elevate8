using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Configuration;
using System.ServiceModel;
using System.ServiceModel.Activation;
using System.Runtime.Serialization;

namespace LegacyApp.Services
{
    [DataContract]
    public class OrderDto
    {
        [DataMember] public int OrderId { get; set; }
        [DataMember] public string CustomerName { get; set; }
        [DataMember] public DateTime OrderDate { get; set; }
        [DataMember] public decimal TotalAmount { get; set; }
        [DataMember] public string Status { get; set; }
    }

    [DataContract]
    public class OrderCreateRequest
    {
        [DataMember] public int CustomerId { get; set; }
        [DataMember] public List<OrderItemRequest> Items { get; set; }
    }

    [DataContract]
    public class OrderItemRequest
    {
        [DataMember] public int ProductId { get; set; }
        [DataMember] public int Quantity { get; set; }
        [DataMember] public decimal UnitPrice { get; set; }
    }

    [DataContract]
    public class ServiceResponse
    {
        [DataMember] public bool Success { get; set; }
        [DataMember] public string Message { get; set; }
        [DataMember] public int? OrderId { get; set; }
    }

    [ServiceContract]
    public interface IOrderService
    {
        [OperationContract]
        List<OrderDto> GetAllOrders();

        [OperationContract]
        OrderDto GetOrderById(int orderId);

        [OperationContract]
        ServiceResponse CreateOrder(OrderCreateRequest request);

        [OperationContract]
        ServiceResponse UpdateOrderStatus(int orderId, string newStatus);

        [OperationContract]
        ServiceResponse CancelOrder(int orderId);
    }

    [AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Allowed)]
    public class OrderService : IOrderService
    {
        private string ConnectionString =>
            ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;

        public List<OrderDto> GetAllOrders()
        {
            var orders = new List<OrderDto>();
            using (var conn = new SqlConnection(ConnectionString))
            {
                conn.Open();
                var cmd = new SqlCommand(
                    @"SELECT o.OrderId, c.CustomerName, o.OrderDate, o.TotalAmount, o.Status
                      FROM Orders o INNER JOIN Customers c ON o.CustomerId = c.CustomerId
                      ORDER BY o.OrderDate DESC", conn);

                using (var reader = cmd.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        orders.Add(new OrderDto
                        {
                            OrderId = reader.GetInt32(0),
                            CustomerName = reader.GetString(1),
                            OrderDate = reader.GetDateTime(2),
                            TotalAmount = reader.GetDecimal(3),
                            Status = reader.GetString(4)
                        });
                    }
                }
            }
            return orders;
        }

        public OrderDto GetOrderById(int orderId)
        {
            using (var conn = new SqlConnection(ConnectionString))
            {
                conn.Open();
                var cmd = new SqlCommand(
                    @"SELECT o.OrderId, c.CustomerName, o.OrderDate, o.TotalAmount, o.Status
                      FROM Orders o INNER JOIN Customers c ON o.CustomerId = c.CustomerId
                      WHERE o.OrderId = @OrderId", conn);
                cmd.Parameters.AddWithValue("@OrderId", orderId);

                using (var reader = cmd.ExecuteReader())
                {
                    if (reader.Read())
                    {
                        return new OrderDto
                        {
                            OrderId = reader.GetInt32(0),
                            CustomerName = reader.GetString(1),
                            OrderDate = reader.GetDateTime(2),
                            TotalAmount = reader.GetDecimal(3),
                            Status = reader.GetString(4)
                        };
                    }
                }
            }
            return null;
        }

        public ServiceResponse CreateOrder(OrderCreateRequest request)
        {
            try
            {
                using (var conn = new SqlConnection(ConnectionString))
                {
                    conn.Open();
                    using (var transaction = conn.BeginTransaction())
                    {
                        var cmd = new SqlCommand(
                            @"INSERT INTO Orders (CustomerId, OrderDate, TotalAmount, Status) 
                              VALUES (@CustomerId, @OrderDate, @Total, 'Pending');
                              SELECT SCOPE_IDENTITY();", conn, transaction);

                        decimal total = 0;
                        foreach (var item in request.Items)
                            total += item.Quantity * item.UnitPrice;

                        cmd.Parameters.AddWithValue("@CustomerId", request.CustomerId);
                        cmd.Parameters.AddWithValue("@OrderDate", DateTime.Now);
                        cmd.Parameters.AddWithValue("@Total", total);

                        int orderId = Convert.ToInt32(cmd.ExecuteScalar());

                        foreach (var item in request.Items)
                        {
                            var itemCmd = new SqlCommand(
                                @"INSERT INTO OrderItems (OrderId, ProductId, Quantity, UnitPrice)
                                  VALUES (@OrderId, @ProductId, @Qty, @Price)", conn, transaction);
                            itemCmd.Parameters.AddWithValue("@OrderId", orderId);
                            itemCmd.Parameters.AddWithValue("@ProductId", item.ProductId);
                            itemCmd.Parameters.AddWithValue("@Qty", item.Quantity);
                            itemCmd.Parameters.AddWithValue("@Price", item.UnitPrice);
                            itemCmd.ExecuteNonQuery();
                        }

                        transaction.Commit();
                        return new ServiceResponse { Success = true, Message = "Order created.", OrderId = orderId };
                    }
                }
            }
            catch (Exception ex)
            {
                return new ServiceResponse { Success = false, Message = ex.Message };
            }
        }

        public ServiceResponse UpdateOrderStatus(int orderId, string newStatus)
        {
            using (var conn = new SqlConnection(ConnectionString))
            {
                conn.Open();
                var cmd = new SqlCommand("UPDATE Orders SET Status = @Status WHERE OrderId = @Id", conn);
                cmd.Parameters.AddWithValue("@Status", newStatus);
                cmd.Parameters.AddWithValue("@Id", orderId);
                int affected = cmd.ExecuteNonQuery();
                return new ServiceResponse
                {
                    Success = affected > 0,
                    Message = affected > 0 ? "Status updated." : "Order not found."
                };
            }
        }

        public ServiceResponse CancelOrder(int orderId)
        {
            return UpdateOrderStatus(orderId, "Cancelled");
        }
    }
}
