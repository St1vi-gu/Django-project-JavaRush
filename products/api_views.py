from django.db import IntegrityError, transaction
from django.db.models import Avg
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from reviews.serializers import ReviewSerializer
from reviews.services import has_purchased

from .filters import ProductFilter, ProductOrderingFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filterset_class = ProductFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, ProductOrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'avg_rating']

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .annotate(avg_rating=Avg('reviews__rating'))
            .order_by('-created_at', 'pk')
        )

        category = self.request.query_params.get('category')
        return qs.filter(category__slug=category) if category else qs

    @extend_schema(methods=['GET'], responses=ReviewSerializer(many=True))
    @extend_schema(methods=['POST'], request=ReviewSerializer, responses={201: ReviewSerializer})
    @action(
        detail=True,
        methods=['get', 'post'],
        pagination_class=None,
        permission_classes=[permissions.IsAuthenticatedOrReadOnly],
    )
    def reviews(self, request, pk=None):
        product = self.get_object()
        if request.method == 'GET':
            return Response(
                ReviewSerializer(product.reviews.select_related('user'), many=True).data
            )
        purchased = has_purchased(request.user, product)
        if not purchased:
            return Response({'detail': 'Review allowed only after purchase.'}, status=403)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if product.reviews.filter(user=request.user).exists():
            return Response({'detail': 'Review already exists.'}, status=400)
        try:
            with transaction.atomic():
                serializer.save(user=request.user, product=product)
        except IntegrityError:
            return Response({'detail': 'Review already exists.'}, status=400)
        return Response(serializer.data, status=201)
