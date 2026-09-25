from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from products.models import Product
from .models import Order, OrderItem

class OutOfStock(Exception):
    pass

@transaction.atomic
def create_order(user, cart, data) -> Order:
    items = list(cart)
    if not items:
        raise ValueError("Cart is empty")

    locked = {
        p.pk: p for p in Product.objects.select_for_update().filter(
            pk__in=[item["product_id"] for item in items]
        )
    }
    order = Order.objects.create(
        user=user,
        status=Order.Status.PENDING,
        total_price=0,
        shipping_address=(
            f'{data["full_name"]}, {data["phone_number"]}\n'
            f'{data["city"]}, {data["address"]}'
        ),
    )
    total = 0
    for item in items:
        product = locked[item["product_id"]]
        if product.stock < item["quantity"]:
            raise OutOfStock(f"Недостаточно {product.name}: доступно {product.stock}")
        product.stock -= item["quantity"]
        product.save(update_fields=["stock"])
        OrderItem.objects.create(
            order=order, product=product, quantity=item["quantity"], price=item["price"]
        )
        total += item["total_price"]

    order.total_price = total
    order.save(update_fields=["total_price"])
    return order

def send_order_email(order: Order) -> None:
    recipients = [order.user.email] if order.user.email else []
    if recipients:
        send_mail(
            f"Hop & Barley — заказ #{order.pk}",
            f"Ваш заказ #{order.pk} создан. Сумма: {order.total_price}.",
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=True,
        )
