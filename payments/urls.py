from django.urls import path

from .views import demo_payment

app_name = 'payments'
urlpatterns = [path('<int:order_id>/demo/', demo_payment, name='demo')]
