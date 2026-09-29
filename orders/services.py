"""Transactional order operations shared by the website, API and admin."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, TypedDict

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from products.models import Product

from .models import Order, OrderItem

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from .cart import Cart
logger = logging.getLogger(__name__)


class OrderError(ValueError):
    """An order cannot be created or moved to the requested state."""


class OutOfStockError(OrderError):
    """A product is unavailable in the requested quantity."""


class OrderLine(TypedDict):
    product_id: int
    quantity: int


def send_order_email(order: Order) -> None:
    """Send after commit; delivery failure must not lose a completed order."""
    if not order.user.email:
        return
    try:
        send_mail(
            f'Hop & Barley — заказ #{order.pk}',
            f'Ваш заказ #{order.pk} создан. Сумма: {order.total_price}.\n'
            f'Способ оплаты: {order.payment.get_method_display()}.\n'
            f'Адрес: {order.shipping_address}',
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Could not send confirmation for order %s', order.pk)


@transaction.atomic
def place_order(user: 'User', items: list[OrderLine], address: str, method: str) -> Order:
    """Reserve current prices and stock and create a matching unpaid payment."""
    from payments.models import Payment

    if method not in Payment.Method.values:
        raise OrderError('Выберите доступный способ оплаты.')
    if method != Payment.Method.COD and not settings.PAYMENT_DEMO_ENABLED:
        raise OrderError('Онлайн-оплата отключена. Выберите оплату при получении.')
    if not items or not address.strip():
        raise OrderError('Укажите товары и адрес доставки.')
    quantities: dict[int, int] = {}
    for item in items:
        if not 1 <= item['quantity'] <= 1_000_000:
            raise OrderError('Некорректное количество товара.')
        pid = item['product_id']
        quantities[pid] = quantities.get(pid, 0) + item['quantity']
    products = {
        p.pk: p
        for p in Product.objects.select_for_update()
        .filter(pk__in=quantities, is_active=True)
        .order_by('pk')
    }
    total = Decimal('0')
    for pid, quantity in quantities.items():
        product = products.get(pid)
        if product is None:
            raise OutOfStockError(f'Товар #{pid} больше недоступен. Обновите корзину.')
        if product.stock < quantity:
            raise OutOfStockError(f'Недостаточно {product.name}: доступно {product.stock}')
        total += product.price * quantity
    if total < 0 or total > Decimal('99999999.99'):
        raise OrderError('Сумма заказа выходит за допустимый диапазон.')
    order = Order.objects.create(
        user=user, status=Order.Status.PENDING, total_price=total, shipping_address=address
    )
    for pid, quantity in quantities.items():
        product = products[pid]
        product.stock -= quantity
        product.save(update_fields=['stock'])
        OrderItem.objects.create(
            order=order, product=product, quantity=quantity, price=product.price
        )
    Payment.objects.create(order=order, method=method)
    transaction.on_commit(lambda: send_order_email(order))
    return order


def create_order(user: 'User', cart: 'Cart', data: dict[str, str]) -> Order:
    """Convert a session cart and checkout form into the shared order input."""
    items: list[OrderLine] = [
        {'product_id': int(pid), 'quantity': item['quantity']} for pid, item in cart.cart.items()
    ]
    address = f'{data["full_name"]}, {data["phone_number"]}\n{data["city"]}, {data["address"]}'
    return place_order(user, items, address, data['payment_type'])


@transaction.atomic
def cancel_order(order_id: int) -> Order:
    """Cancel a pending unpaid order, returning stock exactly once."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.PENDING:
        raise OrderError('Отменить можно только неоплаченный заказ в ожидании.')
    if hasattr(order, 'payment') and order.payment.is_paid:
        raise OrderError('Оплаченный заказ требует отдельного возврата.')
    items = list(order.items.all())
    products = {
        p.pk: p
        for p in Product.objects.select_for_update()
        .filter(pk__in=[item.product_id for item in items])
        .order_by('pk')
    }
    for item in items:
        product = products[item.product_id]
        product.stock += item.quantity
        product.save(update_fields=['stock'])
    order.status = Order.Status.CANCELED
    order.save(update_fields=['status', 'updated_at'])
    return order


@transaction.atomic
def advance_order(order_id: int, status: str) -> Order:
    """Apply fulfillment transitions without bypassing payment rules."""
    from payments.models import Payment

    order = Order.objects.select_for_update().get(pk=order_id)
    payment = Payment.objects.filter(order=order).first()
    can_ship = order.status == Order.Status.PAID or (
        order.status == Order.Status.PENDING
        and payment is not None
        and payment.method == Payment.Method.COD
    )
    can_deliver = order.status == Order.Status.SHIPPED and payment is not None and payment.is_paid
    if not (
        (status == Order.Status.SHIPPED and can_ship)
        or (status == Order.Status.DELIVERED and can_deliver)
    ):
        raise OrderError('Переход недоступен. Проверьте текущий статус и оплату заказа.')
    order.status = status
    order.save(update_fields=['status', 'updated_at'])
    return order
