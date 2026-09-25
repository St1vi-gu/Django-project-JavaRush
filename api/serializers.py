from django.contrib.auth import get_user_model
from rest_framework import serializers
from products.models import Product
from orders.models import Order, OrderItem
from reviews.models import Review

User = get_user_model()

class ProductSerializer(serializers.ModelSerializer):
    rating = serializers.FloatField(source="avg_rating", read_only=True)
    category = serializers.StringRelatedField()
    class Meta:
        model = Product
        fields = ("id","name","slug","description","price","category","image","stock","rating","created_at")

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    class Meta:
        model = OrderItem
        fields = ("id","product","product_name","quantity","price")

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ("id","status","total_price","shipping_address","created_at","items")
        read_only_fields = ("total_price",)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ("id","email","password")
    def create(self, validated_data):
        email = validated_data["email"].lower()
        return User.objects.create_user(username=email, email=email, password=validated_data["password"])

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Review
        fields = ("id","user","rating","comments","created_at")
