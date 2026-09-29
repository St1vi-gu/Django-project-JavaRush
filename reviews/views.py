from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from products.models import Product
from reviews.services import has_purchased

from .forms import ReviewForm


@login_required
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    purchased = has_purchased(request.user, product)
    if not purchased:
        messages.error(request, 'Отзыв можно оставить только после покупки.')
        return redirect(product)
    if product.reviews.filter(user=request.user).exists():
        messages.info(request, 'Вы уже оставили отзыв.')
        return redirect(product)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.product = product
        review.save()
        messages.success(request, 'Спасибо за отзыв!')
    else:
        messages.error(request, 'Проверьте рейтинг и комментарий.')
    return redirect(product)
