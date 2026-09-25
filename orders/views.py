from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from products.models import Product
from .cart import Cart
from .forms import CheckoutForm
from .services import OutOfStock, create_order, send_order_email

def cart_detail(request):
    return render(request, "cart.html", {"cart": Cart(request)})

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        quantity = 1
    current = next((i["quantity"] for i in cart if i["product_id"] == product_id), 0)
    if current + quantity > product.stock:
        messages.error(request, f"В наличии только {product.stock} шт.")
    else:
        cart.add(product, quantity)
        messages.success(request, f"{product.name} добавлен в корзину")
    return redirect("orders:cart_detail")

@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1
    if quantity <= 0:
        cart.remove(product)
    elif quantity > product.stock:
        messages.error(request, f"В наличии только {product.stock} шт.")
    else:
        cart.add(product, quantity, override=True)
    return redirect("orders:cart_detail")

@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).remove(product)
    messages.info(request, f"{product.name} удалён из корзины")
    return redirect("orders:cart_detail")

@login_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.info(request, "Корзина пуста")
        return redirect("products:list")
    initial = {}
    profile = getattr(request.user, "profile", None)
    if profile:
        initial = {"full_name": profile.full_name, "city": profile.city,
                   "address": profile.address, "phone_number": profile.phone}
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            order = create_order(request.user, cart, form.cleaned_data)
        except OutOfStock as exc:
            messages.error(request, str(exc))
        else:
            send_order_email(order)
            cart.clear()
            messages.success(request, f"Заказ #{order.pk} создан")
            return redirect("users:account")
    return render(request, "checkout.html", {"form": form, "cart": cart})
