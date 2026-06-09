using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;

namespace LegacyApp.Endpoints;

/// <summary>Order data transfer object.</summary>
public record OrderDto(int OrderId, string CustomerName, DateTime OrderDate, decimal TotalAmount, string Status);

/// <summary>Request payload for creating a new order.</summary>
public record CreateOrderRequest(int CustomerId, List<OrderItemRequest> Items);
public record OrderItemRequest(int ProductId, int Quantity, decimal UnitPrice);

/// <summary>Standard API response envelope.</summary>
public record ServiceResponse(bool Success, string Message, int? OrderId = null);

/// <summary>Minimal API endpoints replacing the WCF OrderService.</summary>
public static class OrderEndpoints
{
    public static RouteGroupBuilder MapOrderEndpoints(this RouteGroupBuilder group)
    {
        group.MapGet("/", GetAllOrders).WithName("GetOrders").WithOpenApi();
        group.MapGet("/{id:int}", GetOrderById).WithName("GetOrder").WithOpenApi();
        group.MapPost("/", CreateOrder).WithName("CreateOrder").WithOpenApi();
        group.MapPut("/{id:int}/status", UpdateStatus).WithName("UpdateOrderStatus").WithOpenApi();
        group.MapDelete("/{id:int}", CancelOrder).WithName("CancelOrder").WithOpenApi();
        return group;
    }

    private static async Task<Ok<List<OrderDto>>> GetAllOrders(AppDbContext db)
    {
        var orders = await db.Orders
            .Include(o => o.Customer)
            .OrderByDescending(o => o.OrderDate)
            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
            .ToListAsync();
        return TypedResults.Ok(orders);
    }

    private static async Task<Results<Ok<OrderDto>, NotFound>> GetOrderById(int id, AppDbContext db)
    {
        var order = await db.Orders.Include(o => o.Customer)
            .Where(o => o.OrderId == id)
            .Select(o => new OrderDto(o.OrderId, o.Customer.CustomerName, o.OrderDate, o.TotalAmount, o.Status))
            .FirstOrDefaultAsync();
        return order is not null ? TypedResults.Ok(order) : TypedResults.NotFound();
    }

    private static async Task<Created<ServiceResponse>> CreateOrder(CreateOrderRequest req, AppDbContext db)
    {
        var total = req.Items.Sum(i => i.Quantity * i.UnitPrice);
        var order = new Order
        {
            CustomerId = req.CustomerId,
            OrderDate = DateTime.UtcNow,
            TotalAmount = total,
            Status = "Pending",
            Items = req.Items.Select(i => new OrderItem
            {
                ProductId = i.ProductId,
                Quantity = i.Quantity,
                UnitPrice = i.UnitPrice
            }).ToList()
        };

        db.Orders.Add(order);
        await db.SaveChangesAsync();

        return TypedResults.Created($"/api/orders/{order.OrderId}",
            new ServiceResponse(true, "Order created.", order.OrderId));
    }

    private static async Task<Results<Ok<ServiceResponse>, NotFound>> UpdateStatus(
        int id, string newStatus, AppDbContext db)
    {
        var order = await db.Orders.FindAsync(id);
        if (order is null) return TypedResults.NotFound();
        order.Status = newStatus;
        await db.SaveChangesAsync();
        return TypedResults.Ok(new ServiceResponse(true, "Status updated."));
    }

    private static async Task<Results<Ok<ServiceResponse>, NotFound>> CancelOrder(int id, AppDbContext db)
    {
        var order = await db.Orders.FindAsync(id);
        if (order is null) return TypedResults.NotFound();
        order.Status = "Cancelled";
        await db.SaveChangesAsync();
        return TypedResults.Ok(new ServiceResponse(true, "Order cancelled."));
    }
}