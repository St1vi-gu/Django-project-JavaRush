from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import ProductViewSet, OrderViewSet, RegisterAPIView
router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("orders", OrderViewSet, basename="order")
urlpatterns = [
    path("", include(router.urls)),
    path("users/register/", RegisterAPIView.as_view(), name="register"),
    path("users/login/", TokenObtainPairView.as_view(), name="login"),
    path("users/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
