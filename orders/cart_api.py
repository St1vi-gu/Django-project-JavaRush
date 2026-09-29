from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .cart import Cart


class CartInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartLineSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=18, decimal_places=2)


class CartResponseSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True)
    total_price = serializers.DecimalField(max_digits=18, decimal_places=2)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)


class CartAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=CartResponseSerializer)
    def get(self, request):
        cart = Cart(request)
        return Response(
            {
                'items': [{k: v for k, v in item.items() if k != 'product'} for item in cart],
                'total_price': cart.get_total_price(),
            }
        )

    @extend_schema(request=CartInputSerializer, responses=CartResponseSerializer)
    def post(self, request):
        return self.update_cart(request, request.data, False)

    def update_cart(self, request, data, override):
        serializer = CartInputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(
            Product, pk=serializer.validated_data['product_id'], is_active=True
        )
        cart = Cart(request)
        quantity = serializer.validated_data['quantity']
        current = cart.cart.get(str(product.pk), {}).get('quantity', 0)
        if (quantity if override else current + quantity) > product.stock:
            raise serializers.ValidationError({'quantity': 'Insufficient stock.'})
        cart.add(product, quantity, override=override)
        return self.get(request)


class CartItemAPIView(CartAPIView):
    http_method_names = ['patch', 'delete', 'options']

    @extend_schema(request=CartQuantitySerializer, responses=CartResponseSerializer)
    def patch(self, request, product_id):
        return self.update_cart(
            request, {'product_id': product_id, 'quantity': request.data.get('quantity')}, True
        )

    @extend_schema(responses={204: None})
    def delete(self, request, product_id):
        cart = Cart(request)
        cart.cart.pop(str(product_id), None)
        cart.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
