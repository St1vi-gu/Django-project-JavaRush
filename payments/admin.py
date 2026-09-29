from django.contrib import admin, messages

from orders.services import OrderError

from .models import Payment
from .services import confirm_payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'is_paid', 'created_at')
    list_filter = ('method', 'is_paid')
    search_fields = ('order__id', 'order__user__email')
    readonly_fields = ('order', 'method', 'is_paid', 'created_at')
    actions = ['record_cash_received']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Подтвердить получение наличных', permissions=['change'])
    def record_cash_received(self, request, queryset):
        for payment in queryset:
            try:
                confirm_payment(payment.order_id, cash=True)
            except OrderError as exc:
                self.message_user(request, f'Заказ #{payment.order_id}: {exc}', messages.WARNING)
            else:
                self.message_user(
                    request, f'Оплата заказа #{payment.order_id} подтверждена.', messages.SUCCESS
                )
