from rest_framework import serializers

from payments.models import Payment

from .models import Order, OrderItem
from .services import OrderError, place_order


class OrderItemSerializer(serializers.ModelSerializer):
    product: serializers.StringRelatedField = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['method', 'is_paid']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'status',
            'total_price',
            'shipping_address',
            'created_at',
            'items',
            'payment',
        ]


class OrderItemWriteSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)


class OrderCreateSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(max_length=1000)
    payment_method = serializers.ChoiceField(
        choices=Payment.Method.choices, default=Payment.Method.COD
    )
    items = OrderItemWriteSerializer(many=True, allow_empty=False)

    def create(self, validated_data):
        try:
            return place_order(
                self.context['request'].user,
                validated_data['items'],
                validated_data['shipping_address'],
                validated_data['payment_method'],
            )
        except OrderError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc
