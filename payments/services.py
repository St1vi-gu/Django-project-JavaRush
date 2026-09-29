from django.conf import settings
from django.db import transaction

from orders.models import Order
from orders.services import OrderError

from .models import Payment


@transaction.atomic
def confirm_payment(order_id: int, *, cash: bool = False) -> Payment:
    """Record payment idempotently; lock in the same order as cancellation."""
    order = Order.objects.select_for_update().get(pk=order_id)
    payment = Payment.objects.select_for_update().get(order=order)
    if cash != (payment.method == Payment.Method.COD):
        raise OrderError('Неверный способ подтверждения оплаты.')
    if not cash and not settings.PAYMENT_DEMO_ENABLED:
        raise OrderError('Онлайн-оплата отключена.')
    if order.status == Order.Status.CANCELED:
        raise OrderError('Отменённый заказ оплатить нельзя.')
    if payment.is_paid:
        return payment
    if order.status not in [Order.Status.PENDING, Order.Status.SHIPPED]:
        raise OrderError('Заказ недоступен для оплаты.')
    payment.is_paid = True
    payment.save(update_fields=['is_paid'])
    if order.status == Order.Status.PENDING:
        order.status = Order.Status.PAID
        order.save(update_fields=['status', 'updated_at'])
    return payment
