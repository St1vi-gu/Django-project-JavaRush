from django.db.models import Avg, Q, F
from django.views.generic import ListView, DetailView

from .models import Product, Category


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
            qs = qs.filter(price__gte=min_price)

        if max_price:
            qs = qs.filter(price__lte=max_price)

        sort = self.request.GET.get('sort', 'new')

        if sort == 'price_asc':
            return qs.order_by('price')

        if sort == 'price_desc':
            return qs.order_by('-price')

        if sort == 'rating':
            return qs.order_by(
                F('avg_rating').desc(nulls_last=True)
            )

        return qs.order_by('-created_at')


    def get_context_data(self,  **kwargs):
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
        from orders.models import Order
        ctx['can_review'] = user.is_authenticated and Order.objects.filter(
            user=user,
            status__in=[Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED],
            items__product=self.object,
        ).exists() and not self.object.reviews.filter(user=user).exists()

        return ctx
