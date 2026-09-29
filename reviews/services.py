from django.db.models import Q

from orders.models import Order


def has_purchased(user, product) -> bool:
    if not user.is_authenticated:
        return False
    return (
        Order.objects.filter(user=user, items__product=product)
        .filter(
            Q(status__in=[Order.Status.PAID, Order.Status.DELIVERED])
            | Q(status=Order.Status.SHIPPED, payment__is_paid=True)
        )
        .exists()
    )
