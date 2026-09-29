from decimal import Decimal, InvalidOperation

from django.db.models import Avg, F, Q
from django.views.generic import DetailView, ListView

from reviews.services import has_purchased

from .models import Category, Product

# Create your views here.


class ProductListView(ListView):
    model = Product
    template_name = 'home.html'
    context_object_name = 'products'
    paginate_by = 9

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .annotate(avg_rating=Avg('reviews__rating'))
        )

        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))

        categories = self.request.GET.getlist('category')

        if categories:
            qs = qs.filter(category__slug__in=categories)

        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')

        if min_price:
            try:
                amount = Decimal(min_price)
                if not amount.is_finite() or amount < 0:
                    return qs.none()
                qs = qs.filter(price__gte=amount)
            except (InvalidOperation, ValueError):
                return qs.none()

        if max_price:
            try:
                amount = Decimal(max_price)
                if not amount.is_finite() or amount < 0:
                    return qs.none()
                qs = qs.filter(price__lte=amount)
            except (InvalidOperation, ValueError):
                return qs.none()

        sort = self.request.GET.get('sort', 'new')

        if sort == 'price_asc':
            return qs.order_by('price')

        if sort == 'price_desc':
            return qs.order_by('-price')

        if sort == 'popular':
            from django.db.models import IntegerField, OuterRef, Subquery, Sum, Value
            from django.db.models.functions import Coalesce

            from orders.models import OrderItem

            sold = (
                OrderItem.objects.filter(product_id=OuterRef('pk'), order__payment__is_paid=True)
                .exclude(order__status='canceled')
                .values('product_id')
                .annotate(total=Sum('quantity'))
                .values('total')
            )
            return qs.annotate(
                sold_count=Coalesce(Subquery(sold, output_field=IntegerField()), Value(0))
            ).order_by('-sold_count', 'pk')

        if sort == 'rating':
            return qs.order_by(F('avg_rating').desc(nulls_last=True))

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        ctx['query'] = self.request.GET.get('q', '')
        ctx['min_price'] = self.request.GET.get('min_price', '')
        ctx['max_price'] = self.request.GET.get('max_price', '')
        ctx['selected_categories'] = self.request.GET.getlist('category')
        ctx['current_sort'] = self.request.GET.get('sort', 'new')

        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['querystring'] = params.urlencode()
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product-detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .annotate(avg_rating=Avg('reviews__rating'))
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reviews'] = self.object.reviews.select_related('user')
        from reviews.forms import ReviewForm

        ctx['review_form'] = ReviewForm()

        user = self.request.user

        ctx['can_review'] = (
            has_purchased(user, self.object) and not self.object.reviews.filter(user=user).exists()
        )

        return ctx
