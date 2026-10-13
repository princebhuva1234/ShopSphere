import logging
from decimal import Decimal
from html import escape

import sib_api_v3_sdk
from django.conf import settings

logger = logging.getLogger(__name__)


def send_transactional_email(recipient_email, subject, html_content):
    """Send a transactional email through Brevo without breaking checkout."""
    if not getattr(settings, "BREVO_API_KEY", None):
        logger.error("Brevo API key is missing.")
        return False

    if not getattr(settings, "DEFAULT_FROM_EMAIL", None):
        logger.error("Brevo sender email is missing.")
        return False

    if not recipient_email:
        logger.warning("Cannot send email: recipient address is missing.")
        return False

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender={"email": settings.DEFAULT_FROM_EMAIL, "name": "ShopSphere"},
        to=[{"email": recipient_email}],
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(email)
        logger.info("Brevo accepted email request: %s", response)
        return True
    except sib_api_v3_sdk.ApiException:
        logger.exception("Brevo API rejected the email request.")
        return False
    except Exception:
        logger.exception("Unexpected error while sending Brevo email.")
        return False


def _order_items_html(order):
    rows = []
    for item in order.items.select_related("product").all():
        name = escape(item.product.name if item.product_id else "Product unavailable")
        price = Decimal(str(item.price or 0))
        quantity = int(item.quantity or 0)
        subtotal = price * quantity
        rows.append(
            "<tr>"
            f"<td style='padding:10px;border-bottom:1px solid #eee'>{name}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #eee'>{quantity}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #eee'>₹{price:,.2f}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #eee'>₹{subtotal:,.2f}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4'>No items found.</td></tr>"


def _base_order_email(order, heading, message):
    customer_name = escape(order.user.get_username())
    status = escape(order.get_status_display())
    total = Decimal(str(order.total_amount or 0))
    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;color:#222;line-height:1.6">
<div style="max-width:680px;margin:20px auto;padding:24px;border:1px solid #eee;border-radius:12px">
<h1 style="color:#0d9488">ShopSphere</h1>
<h2>{heading}</h2>
<p>Hello {customer_name},</p><p>{message}</p>
<p><strong>Order number:</strong> #{order.id}<br>
<strong>Order date:</strong> {order.created_at:%d %B %Y}<br>
<strong>Current status:</strong> {status}</p>
<table style="width:100%;border-collapse:collapse"><thead><tr style="background:#f3f4f6;text-align:left">
<th style="padding:10px">Product</th><th style="padding:10px">Qty</th>
<th style="padding:10px">Price</th><th style="padding:10px">Subtotal</th>
</tr></thead><tbody>{_order_items_html(order)}</tbody></table>
<h3 style="text-align:right">Total: ₹{total:,.2f}</h3>
<p>Thank you for shopping with ShopSphere!</p><p><strong>ShopSphere Team</strong></p>
</div></body></html>"""


def send_order_confirmation_email(order):
    """Email the customer after the order payment has been verified."""
    recipient = getattr(order.user, "email", "")
    if not recipient:
        logger.warning("Order #%s has no customer email address.", order.id)
        return False
    html = _base_order_email(
        order,
        "Your order is confirmed!",
        "Your order has been placed and confirmed successfully.",
    )
    return send_transactional_email(
        recipient,
        f"ShopSphere Order Confirmation - #{order.id}",
        html,
    )


def send_payment_confirmation_email(order, payment):
    """Email payment details after Razorpay verification succeeds."""
    recipient = getattr(order.user, "email", "")
    if not recipient:
        logger.warning("Order #%s has no customer email address.", order.id)
        return False
    amount = Decimal(str(payment.amount or 0))
    payment_id = escape(payment.provider_payment_id or "Not available")
    html = _base_order_email(
        order,
        "Payment received successfully",
        f"We have verified your payment of ₹{amount:,.2f}. "
        f"Payment reference: {payment_id}.",
    )
    return send_transactional_email(
        recipient,
        f"ShopSphere Payment Confirmation - Order #{order.id}",
        html,
    )


def send_order_status_email(order, new_status):
    """Email the customer when an order is shipped, delivered, or cancelled."""
    recipient = getattr(order.user, "email", "")
    if not recipient:
        logger.warning("Order #%s has no customer email address.", order.id)
        return False

    messages = {
        "PROCESSING": "Your order is now being prepared.",
        "SHIPPED": "Good news! Your order has been shipped and is on its way.",
        "DELIVERED": "Your order has been delivered successfully.",
        "CANCELLED": "Your order has been cancelled.",
    }
    message = messages.get(new_status)
    if not message:
        return False

    status_title = order.get_status_display()
    html = _base_order_email(order, f"Order {status_title}", message)
    return send_transactional_email(
        recipient,
        f"ShopSphere Order {status_title} - #{order.id}",
        html,
    )
