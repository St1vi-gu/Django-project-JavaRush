from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ProfileForm, RegisterForm
from .models import Profile


def register_view(request):
    if request.user.is_authenticated:
        return redirect('products:list')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)

        messages.success(request, 'Добро пожаловать в Hop & Barley')

        return redirect('products:list')

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('products:list')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)

            next_url = request.GET.get('next')

            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect('products:list')

        messages.error(request, 'Неверный email или пароль')

    return render(request, 'login.html')


@require_POST
def logout_view(request):
    logout(request)

    messages.success(request, 'Вы успешно вышли из аккаунта')

    return redirect('products:list')


@login_required
def account_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    form = ProfileForm(request.POST or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        form.save()

        messages.success(request, 'Профиль обновлён')

        return redirect('users:account')

    orders = (
        request.user.orders.select_related('payment')
        .prefetch_related('items__product')
        .order_by('-created_at')
    )

    status = request.GET.get('status')

    if status:
        orders = orders.filter(status=status)

    return render(
        request,
        'account.html',
        {
            'form': form,
            'orders': orders,
        },
    )
