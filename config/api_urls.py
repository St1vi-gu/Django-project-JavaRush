from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from orders.api_views import OrderViewSet
from orders.cart_api import CartAPIView, CartItemAPIView
from products.api_views import CategoryViewSet, ProductViewSet
from users.api_views import RegisterAPIView

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('categories', CategoryViewSet, basename='category')
router.register('orders', OrderViewSet, basename='order')
urlpatterns = [
    path('', include(router.urls)),
    path('users/register/', RegisterAPIView.as_view(), name='register'),
    path('users/login/', TokenObtainPairView.as_view(), name='login'),
    path('users/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh_alias'),
    path('cart/', CartAPIView.as_view(), name='cart-api'),
    path('cart/<int:product_id>/', CartItemAPIView.as_view(), name='cart-item-api'),
]
