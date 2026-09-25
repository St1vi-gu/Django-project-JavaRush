from django.db.models import Avg, Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from products.models import Product
from orders.models import Order
from reviews.models import Review
from .serializers import ProductSerializer, OrderSerializer, RegisterSerializer, ReviewSerializer

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category").annotate(avg_rating=Avg("reviews__rating"))
        q = self.request.query_params.get("search")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)
        return qs

    @action(detail=True, methods=["get","post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def reviews(self, request, pk=None):
        product = self.get_object()
        if request.method == "GET":
            return Response(ReviewSerializer(product.reviews.all(), many=True).data)
        purchased = Order.objects.filter(
            user=request.user, items__product=product,
            status__in=[Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED]
        ).exists()
        if not purchased:
            return Response({"detail":"Review allowed only after purchase."}, status=403)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if product.reviews.filter(user=request.user).exists():
            return Response({"detail":"Review already exists."}, status=400)
        serializer.save(user=request.user, product=product)
        return Response(serializer.data, status=201)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, total_price=0)
    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status not in [Order.Status.PENDING]:
            return Response({"detail":"Only pending orders can be cancelled."}, status=400)
        order.status = Order.Status.CANCELED
        order.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)

class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
