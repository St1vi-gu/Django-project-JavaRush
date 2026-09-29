from django.db.models import F
from django.db.models.expressions import OrderBy
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from .models import Product


class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = filters.CharFilter(field_name='category__slug')

    class Meta:
        model = Product
        fields = ['category__name', 'category__slug']


class ProductOrderingFilter(OrderingFilter):
    """Always put unrated products after rated products on PostgreSQL too."""

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset
        expressions: list[str | OrderBy] = []
        for field in ordering:
            if field.lstrip('-') == 'avg_rating':
                rating = F('avg_rating')
                expressions.append(
                    rating.desc(nulls_last=True)
                    if field.startswith('-')
                    else rating.asc(nulls_last=True)
                )
            else:
                expressions.append(field)
        return queryset.order_by(*expressions)
