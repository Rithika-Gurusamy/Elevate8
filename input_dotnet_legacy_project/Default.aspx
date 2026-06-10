<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Default.aspx.cs" Inherits="LegacyApp.Default" %>

<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head runat="server">
    <title>Legacy App - Dashboard</title>
    <link href="~/Content/Site.css" rel="stylesheet" type="text/css" />
</head>
<body>
    <form id="form1" runat="server">
        <asp:ScriptManager ID="ScriptManager1" runat="server" />
        
        <div class="container">
            <h1>Enterprise Dashboard</h1>
            
            <asp:UpdatePanel ID="UpdatePanel1" runat="server">
                <ContentTemplate>
                    <asp:GridView ID="OrdersGrid" runat="server" 
                        AutoGenerateColumns="False"
                        CssClass="table table-striped"
                        DataKeyNames="OrderId"
                        OnRowCommand="OrdersGrid_RowCommand"
                        AllowPaging="True"
                        PageSize="25"
                        OnPageIndexChanging="OrdersGrid_PageIndexChanging">
                        <Columns>
                            <asp:BoundField DataField="OrderId" HeaderText="Order #" />
                            <asp:BoundField DataField="CustomerName" HeaderText="Customer" />
                            <asp:BoundField DataField="OrderDate" HeaderText="Date" DataFormatString="{0:MM/dd/yyyy}" />
                            <asp:BoundField DataField="TotalAmount" HeaderText="Total" DataFormatString="{0:C}" />
                            <asp:TemplateField HeaderText="Status">
                                <ItemTemplate>
                                    <asp:Label ID="StatusLabel" runat="server" 
                                        Text='<%# Eval("Status") %>'
                                        CssClass='<%# GetStatusCssClass(Eval("Status").ToString()) %>' />
                                </ItemTemplate>
                            </asp:TemplateField>
                            <asp:ButtonField ButtonType="Button" Text="View" CommandName="ViewOrder" />
                        </Columns>
                    </asp:GridView>
                    
                    <asp:Label ID="lblTotalOrders" runat="server" CssClass="summary-label" />
                    <asp:Label ID="lblTotalRevenue" runat="server" CssClass="summary-label" />
                </ContentTemplate>
                <Triggers>
                    <asp:AsyncPostBackTrigger ControlID="btnRefresh" EventName="Click" />
                </Triggers>
            </asp:UpdatePanel>
            
            <asp:Button ID="btnRefresh" runat="server" Text="Refresh Data" OnClick="btnRefresh_Click" CssClass="btn btn-primary" />
            <asp:Button ID="btnExport" runat="server" Text="Export to Excel" OnClick="btnExport_Click" CssClass="btn btn-success" />
        </div>
    </form>
</body>
</html>
