from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum

from .models import Order, OrderItem


def sales_summary(orders):
    paid = orders.filter(payment__is_paid=True).exclude(status=Order.Status.CANCELED)
    line_total = ExpressionWrapper(
        F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2)
    )
    top_products = (
        OrderItem.objects.filter(order__in=paid)
        .values('product_id', 'product__name')
        .annotate(units=Sum('quantity'), revenue=Sum(line_total))
        .order_by('-units', 'product_id')[:10]
    )
    return {
        'order_count': orders.count(),
        'paid_count': paid.count(),
        'revenue': paid.aggregate(total=Sum('total_price'))['total'] or Decimal('0'),
        'by_status': list(
            orders.order_by().values('status').annotate(count=Count('pk')).order_by('status')
        ),
        'top_products': list(top_products),
    }
