from django.db import models
from orders.models import Order
class Payment(models.Model):
    class Method(models.TextChoices):
        DEBIT="debit","Debit card"
        WALLET="wallet","Wallet"
        COD="cod","Cash on delivery"
    order=models.OneToOneField(Order,on_delete=models.CASCADE,related_name="payment")
    method=models.CharField(max_length=20,choices=Method.choices)
    is_paid=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Payment for order #{self.order_id}"
