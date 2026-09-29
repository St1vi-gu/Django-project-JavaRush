from django.db import models

from orders.models import Order


class Payment(models.Model):
    class Method(models.TextChoices):
        DEBIT = 'debit', 'Оплата картой'
        WALLET = 'wallet', 'Оплата криптой'
        COD = 'cod', 'Оплата при получении'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=Method.choices)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Payment for order #{self.order_id}'
