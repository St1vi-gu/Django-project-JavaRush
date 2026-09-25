from django.contrib import admin
from django.db.models import Sum
from .models import Order, OrderItem
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
@admin.action(description="Mark selected orders as shipped")
def mark_shipped(modeladmin, request, queryset):
    queryset.filter(status=Order.Status.PAID).update(status=Order.Status.SHIPPED)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id","user","status","total_price","created_at")
    list_filter = ("status","created_at")
    search_fields = ("id","user__username","user__email","shipping_address")
    actions = [mark_shipped]
    inlines = [OrderItemInline]
