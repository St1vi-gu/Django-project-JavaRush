from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .cart import Cart
from .forms import CheckoutForm
from .services import OrderError, cancel_order, create_order


def cart_detail(request):
    return render(request, 'cart.html', {'cart': Cart(request)})


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except ValueError:
        quantity = 1
    current = next((i['quantity'] for i in cart if i['product_id'] == product_id), 0)
    if current + quantity > product.stock:
        messages.error(request, f'В наличии только {product.stock} шт.')
    else:
        cart.add(product, quantity)
        messages.success(request, f'{product.name} добавлен в корзину')
    return redirect('orders:cart_detail')


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    if quantity <= 0:
        cart.remove(product)
    elif quantity > product.stock:
        messages.error(request, f'В наличии только {product.stock} шт.')
    else:
        cart.add(product, quantity, override=True)
    return redirect('orders:cart_detail')


@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).remove(product)
    messages.info(request, f'{product.name} удалён из корзины')
    return redirect('orders:cart_detail')


@login_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.info(request, 'Корзина пуста')
        return redirect('products:list')
    initial = {}
    profile = getattr(request.user, 'profile', None)
    if profile:
        initial = {
            'full_name': profile.full_name,
            'city': profile.city,
            'address': profile.address,
            'phone_number': profile.phone,
        }
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            order = create_order(request.user, cart, form.cleaned_data)
        except OrderError as exc:
            messages.error(request, str(exc))
        else:
            cart.clear()
            messages.success(request, f'Заказ #{order.pk} создан')
            if order.payment.method != 'cod':
                return redirect('payments:demo', order_id=order.pk)
            return redirect('users:account')
    return render(request, 'checkout.html', {'form': form, 'cart': cart})


@login_required
@require_POST
def cancel(request, order_id):
    from .models import Order

    order = get_object_or_404(Order, pk=order_id, user=request.user)
    try:
        cancel_order(order.pk)
    except OrderError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, 'Заказ отменён, товары возвращены на склад.')
    return redirect('users:account')


@require_POST
def cart_clear(request):
    Cart(request).clear()
    messages.success(request, 'Корзина очищена.')
    return redirect('orders:cart_detail')
