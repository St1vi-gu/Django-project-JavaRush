from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path

from .analytics import sales_summary
from .models import Order, OrderItem
from .services import OrderError, advance_order, cancel_order


class DateRangeForm(forms.Form):
    start = forms.DateField(
        required=False, label='С даты', widget=forms.DateInput(attrs={'type': 'date'})
    )
    end = forms.DateField(
        required=False, label='По дату', widget=forms.DateInput(attrs={'type': 'date'})
    )

    def clean(self):
        data = super().clean() or {}
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError('Начальная дата должна быть не позже конечной.')
        return data


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'quantity', 'price')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at', 'payment__method')
    search_fields = ('id', 'user__username', 'user__email', 'shipping_address')
    readonly_fields = ('user', 'status', 'total_price', 'created_at', 'updated_at')
    actions = ['mark_shipped', 'mark_delivered', 'cancel_pending']
    inlines = [OrderItemInline]
    change_list_template = 'admin/orders/order/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        return [
            path(
                'analytics/',
                self.admin_site.admin_view(self.analytics),
                name='orders_order_analytics',
            ),
            *super().get_urls(),
        ]

    def analytics(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        form = DateRangeForm(request.GET)
        orders = Order.objects.all()
        if form.is_valid():
            if form.cleaned_data['start']:
                orders = orders.filter(created_at__date__gte=form.cleaned_data['start'])
            if form.cleaned_data['end']:
                orders = orders.filter(created_at__date__lte=form.cleaned_data['end'])
        else:
            orders = orders.none()
        context = {
            **self.admin_site.each_context(request),
            'title': 'Аналитика магазина',
            'form': form,
            **sales_summary(orders),
        }
        return TemplateResponse(request, 'admin/orders/analytics.html', context)

    def apply_transition(self, request, queryset, target):
        done = 0
        for order in queryset:
            try:
                if target == Order.Status.CANCELED:
                    cancel_order(order.pk)
                else:
                    advance_order(order.pk, target)
                done += 1
            except OrderError as exc:
                self.message_user(request, f'Заказ #{order.pk}: {exc}', messages.WARNING)
        self.message_user(request, f'Обновлено заказов: {done}', messages.SUCCESS)

    @admin.action(description='Отправить выбранные заказы', permissions=['change'])
    def mark_shipped(self, request, queryset):
        self.apply_transition(request, queryset, Order.Status.SHIPPED)

    @admin.action(description='Отметить доставленными (после оплаты)', permissions=['change'])
    def mark_delivered(self, request, queryset):
        self.apply_transition(request, queryset, Order.Status.DELIVERED)

    @admin.action(
        description='Отменить неоплаченные заказы и вернуть остатки', permissions=['change']
    )
    def cancel_pending(self, request, queryset):
        self.apply_transition(request, queryset, Order.Status.CANCELED)
