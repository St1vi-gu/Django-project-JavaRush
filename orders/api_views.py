from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.models import Payment
from payments.services import confirm_payment

from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer
from .services import OrderError, cancel_order


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        user_id = self.request.user.pk
        if user_id is None:
            return Order.objects.none()
        return (
            Order.objects.filter(user_id=user_id)
            .select_related('payment')
            .prefetch_related('items__product')
        )

    def get_serializer_class(self):
        return OrderCreateSerializer if self.action == 'create' else OrderSerializer

    @extend_schema(request=OrderCreateSerializer, responses={201: OrderSerializer})
    def create(self, request, *args, **kwargs):
        write = self.get_serializer(data=request.data)
        write.is_valid(raise_exception=True)
        order = write.save()
        return Response(
            OrderSerializer(order, context=self.get_serializer_context()).data, status=201
        )

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            cancel_order(order.pk)
        except OrderError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=['post'], url_path='demo-pay')
    def demo_pay(self, request, pk=None):
        order = self.get_object()
        get_object_or_404(Payment, order=order)
        try:
            confirm_payment(order.pk)
        except OrderError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc
        order.refresh_from_db()
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)
