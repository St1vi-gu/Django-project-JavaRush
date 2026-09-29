from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from orders.services import OrderError

from .models import Payment
from .services import confirm_payment


@login_required
@require_http_methods(['GET', 'POST'])
def demo_payment(request, order_id):
    if not settings.PAYMENT_DEMO_ENABLED:
        raise Http404
    payment = get_object_or_404(
        Payment.objects.select_related('order'), order_id=order_id, order__user=request.user
    )
    if payment.method == Payment.Method.COD:
        raise Http404
    if request.method == 'POST':
        try:
            confirm_payment(order_id)
        except OrderError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Оплата подтверждена.')
        return redirect('users:account')
    return render(request, 'payments/demo.html', {'payment': payment})
