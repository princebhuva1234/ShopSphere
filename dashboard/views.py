from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
)
from django.shortcuts import redirect, render
from django.utils import timezone

from orders.models import Order, OrderItem
from payments.models import Payment
from products.models import Product


User = get_user_model()


# =========================================================
# ADMIN SALES DASHBOARD
# =========================================================

@login_required
def admin_dashboard(request):
    """
    Display sales analytics and order statistics.

    Access is restricted to Django staff/superuser accounts
    and users whose role is ADMIN.
    """

    # -----------------------------------------------------
    # 1. CHECK ADMIN PERMISSIONS
    # -----------------------------------------------------

    is_admin = (
        request.user.is_superuser
        or request.user.is_staff
        or getattr(request.user, "role", None) == "ADMIN"
    )

    if not is_admin:
        messages.error(
            request,
            "You do not have permission to access the admin dashboard.",
        )
        return redirect("product_list")

    # -----------------------------------------------------
    # 2. DATE RANGE
    # -----------------------------------------------------

    today = timezone.localdate()

    month_start = today.replace(day=1)

    # -----------------------------------------------------
    # 3. TOTAL REVENUE
    # -----------------------------------------------------
    #
    # Revenue comes from successful payments only.
    # Failed and pending payments are not counted.
    # -----------------------------------------------------

    paid_payments = Payment.objects.filter(
        status="PAID"
    )

    total_revenue = (
        paid_payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # Revenue for the current month.
    monthly_revenue = (
        paid_payments.filter(
            order__created_at__date__gte=month_start,
            order__created_at__date__lte=today,
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # Revenue for today.
    today_revenue = (
        paid_payments.filter(
            order__created_at__date=today,
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # -----------------------------------------------------
    # 4. ORDER STATISTICS
    # -----------------------------------------------------

    total_orders = Order.objects.count()

    paid_orders = Order.objects.filter(
        payment__status="PAID"
    ).count()

    pending_orders = Order.objects.filter(
        status="PENDING"
    ).count()

    processing_orders = Order.objects.filter(
        status="PROCESSING"
    ).count()

    shipped_orders = Order.objects.filter(
        status="SHIPPED"
    ).count()

    delivered_orders = Order.objects.filter(
        status="DELIVERED"
    ).count()

    cancelled_orders = Order.objects.filter(
        status="CANCELLED"
    ).count()

    orders_today = Order.objects.filter(
        created_at__date=today
    ).count()

    # Average revenue per successfully paid order.
    if paid_orders:
        average_order_value = (
            total_revenue / Decimal(paid_orders)
        ).quantize(
            Decimal("0.01")
        )
    else:
        average_order_value = Decimal("0.00")

    # -----------------------------------------------------
    # 5. CUSTOMER AND SELLER STATISTICS
    # -----------------------------------------------------

    total_customers = User.objects.filter(
        role="CUSTOMER"
    ).count()

    total_sellers = User.objects.filter(
        role="SELLER"
    ).count()

    total_users = User.objects.count()

    # -----------------------------------------------------
    # 6. PRODUCT STATISTICS
    # -----------------------------------------------------

    total_products = Product.objects.count()

    active_products = Product.objects.filter(
        is_active=True
    ).count()

    inactive_products = Product.objects.filter(
        is_active=False
    ).count()

    low_stock_products = Product.objects.filter(
        is_active=True,
        stock_quantity__gt=0,
        stock_quantity__lte=5,
    ).count()

    out_of_stock_products = Product.objects.filter(
        is_active=True,
        stock_quantity=0,
    ).count()

    # -----------------------------------------------------
    # 7. RECENT ORDERS
    # -----------------------------------------------------

    recent_orders = (
        Order.objects
        .select_related("user", "payment")
        .prefetch_related("items__product")
        .order_by("-created_at")[:10]
    )

    # -----------------------------------------------------
    # 8. TOP-SELLING PRODUCTS
    # -----------------------------------------------------
    #
    # Only products belonging to successfully paid orders
    # contribute to sales figures.
    # -----------------------------------------------------

    line_revenue = ExpressionWrapper(
        F("price") * F("quantity"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2,
        ),
    )

    top_products = (
        OrderItem.objects
        .filter(
            order__payment__status="PAID"
        )
        .values(
            "product_id",
            "product__name",
        )
        .annotate(
            units_sold=Sum("quantity"),
            revenue=Sum(line_revenue),
        )
        .order_by(
            "-units_sold",
            "-revenue",
        )[:5]
    )

    # -----------------------------------------------------
    # 9. DAILY SALES FOR THE LAST SEVEN DAYS
    # -----------------------------------------------------

    sales_chart = []

    for offset in range(6, -1, -1):

        sales_day = today - timedelta(days=offset)

        daily_revenue = (
            paid_payments.filter(
                order__created_at__date=sales_day
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        sales_chart.append(
            {
                "date": sales_day,
                "label": sales_day.strftime("%d %b"),
                "amount": daily_revenue,
            }
        )

    # Calculate relative bar heights.
    maximum_daily_revenue = max(
        (
            item["amount"]
            for item in sales_chart
        ),
        default=Decimal("0.00"),
    )

    for item in sales_chart:

        if maximum_daily_revenue > 0:

            item["bar_width"] = int(
                item["amount"]
                / maximum_daily_revenue
                * 100
            )

        else:

            item["bar_width"] = 0

    # -----------------------------------------------------
    # 10. ORDER STATUS SUMMARY
    # -----------------------------------------------------

    order_status_summary = [
        {
            "label": "Pending",
            "count": pending_orders,
            "color": "#f59e0b",
        },
        {
            "label": "Processing",
            "count": processing_orders,
            "color": "#8b5cf6",
        },
        {
            "label": "Shipped",
            "count": shipped_orders,
            "color": "#06b6d4",
        },
        {
            "label": "Delivered",
            "count": delivered_orders,
            "color": "#16a34a",
        },
        {
            "label": "Cancelled",
            "count": cancelled_orders,
            "color": "#dc2626",
        },
    ]

    # -----------------------------------------------------
    # 11. DASHBOARD CONTEXT
    # -----------------------------------------------------

    context = {
        # Revenue
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "today_revenue": today_revenue,
        "average_order_value": average_order_value,

        # Orders
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "pending_orders": pending_orders,
        "processing_orders": processing_orders,
        "shipped_orders": shipped_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "orders_today": orders_today,

        # Users
        "total_customers": total_customers,
        "total_sellers": total_sellers,
        "total_users": total_users,

        # Products
        "total_products": total_products,
        "active_products": active_products,
        "inactive_products": inactive_products,
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,

        # Tables and charts
        "recent_orders": recent_orders,
        "top_products": top_products,
        "sales_chart": sales_chart,
        "order_status_summary": order_status_summary,

        # Dates
        "today": today,
    }

    return render(
        request,
        "dashboard/admin_dashboard.html",
        context,
    )