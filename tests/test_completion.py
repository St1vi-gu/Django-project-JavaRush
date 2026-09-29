from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.db.models.deletion import ProtectedError
from django.test import Client
from rest_framework.test import APIClient

from orders.analytics import sales_summary
from orders.forms import CheckoutForm
from orders.models import Order
from orders.services import OrderError, advance_order, cancel_order, place_order
from payments.models import Payment
from payments.services import confirm_payment
from products.models import Category, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def buyer():
    return get_user_model().objects.create_user(
        username='buyer@example.com', email='buyer@example.com', password='Testing-12345!'
    )


@pytest.fixture
def item():
    category = Category.objects.create(name='Test grain', slug='test-grain')
    return Product.objects.create(
        name='Test grain',
        slug='test-grain-product',
        category=category,
        price=Decimal('12.50'),
        stock=10,
    )


@pytest.fixture
def browser(buyer):
    client = Client()
    client.force_login(buyer)
    return client


def make_order(buyer, item, method='debit', quantity=2):
    return place_order(buyer, [{'product_id': item.pk, 'quantity': quantity}], 'Tallinn', method)


def checkout_data(method='debit'):
    return {
        'full_name': 'Test Buyer',
        'phone_number': '+372123456',
        'city': 'Tallinn',
        'address': 'Test street',
        'payment_type': method,
    }


@pytest.mark.parametrize('method', ['debit', 'wallet', 'cod'])
def test_checkout_payment_and_email(
    browser, buyer, item, method, django_capture_on_commit_callbacks
):
    browser.post(f'/orders/cart/add/{item.pk}/', {'quantity': 2})
    with django_capture_on_commit_callbacks(execute=True):
        response = browser.post('/orders/checkout/', checkout_data(method))
    assert response.status_code == 302
    order = Order.objects.get(user=buyer)
    assert order.total_price == Decimal('25.00')
    assert order.payment.method == method
    assert not order.payment.is_paid
    assert browser.session.get('cart', {}) == {}
    item.refresh_from_db()
    assert item.stock == 8
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [buyer.email]
    assert '25.00' in mail.outbox[0].body
    if method == 'cod':
        assert response.url == '/users/account/'
    else:
        assert response.url == f'/payments/{order.pk}/demo/'


def test_email_failure_does_not_repeat_order(
    browser, buyer, item, django_capture_on_commit_callbacks, caplog
):
    browser.post(f'/orders/cart/add/{item.pk}/', {'quantity': 1})
    with (
        patch('orders.services.send_mail', side_effect=OSError('mail unavailable')),
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = browser.post('/orders/checkout/', checkout_data())
    assert response.status_code == 302
    assert Order.objects.filter(user=buyer).count() == 1
    assert browser.session.get('cart', {}) == {}
    assert 'Could not send confirmation' in caplog.text


def test_checkout_uses_current_price(browser, buyer, item):
    browser.post(f'/orders/cart/add/{item.pk}/', {'quantity': 2})
    item.price = Decimal('17.00')
    item.save()
    assert browser.get('/orders/cart/').context['cart'].get_total_price() == Decimal('34.00')
    assert browser.post('/orders/checkout/', checkout_data()).status_code == 302
    order = Order.objects.get(user=buyer)
    assert order.total_price == Decimal('34.00')
    assert order.items.get().price == Decimal('17.00')


@pytest.mark.parametrize('reason', ['inactive', 'stock', 'removed'])
def test_checkout_invalid_cart_preserves_state(
    browser, buyer, item, reason, django_capture_on_commit_callbacks
):
    browser.post(f'/orders/cart/add/{item.pk}/', {'quantity': 2})
    if reason == 'inactive':
        item.is_active = False
        item.save()
    elif reason == 'stock':
        item.stock = 1
        item.save()
    else:
        item.delete()
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = browser.post('/orders/checkout/', checkout_data())
    assert response.status_code == 200
    assert not Order.objects.filter(user=buyer).exists()
    assert not Payment.objects.exists()
    assert callbacks == []
    assert browser.session.get('cart')


def test_payment_methods_are_validated():
    assert not CheckoutForm(checkout_data('arbitrary')).is_valid()


def test_demo_payment_is_idempotent(browser, buyer, item):
    order = make_order(buyer, item)
    url = f'/payments/{order.pk}/demo/'
    assert browser.get(url).status_code == 200
    order.payment.refresh_from_db()
    assert not order.payment.is_paid
    for _ in range(2):
        assert browser.post(url).status_code == 302
    order.refresh_from_db()
    item.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert order.payment.is_paid
    assert item.stock == 8
    assert Payment.objects.filter(order=order).count() == 1
    with pytest.raises(OrderError):
        cancel_order(order.pk)


def test_demo_requires_owner(browser, buyer, item):
    other = get_user_model().objects.create_user(username='other')
    order = make_order(other, item)
    assert browser.get(f'/payments/{order.pk}/demo/').status_code == 404
    assert browser.post(f'/payments/{order.pk}/demo/').status_code == 404
    assert browser.post(f'/orders/{order.pk}/cancel/').status_code == 404


def test_demo_requires_csrf(buyer, item):
    order = make_order(buyer, item)
    client = Client(enforce_csrf_checks=True)
    client.force_login(buyer)
    assert client.post(f'/payments/{order.pk}/demo/').status_code == 403


def test_cancel_then_pay(browser, buyer, item):
    order = make_order(buyer, item)
    assert browser.post(f'/orders/{order.pk}/cancel/').status_code == 302
    assert browser.post(f'/payments/{order.pk}/demo/').status_code == 302
    order.refresh_from_db()
    item.refresh_from_db()
    assert order.status == Order.Status.CANCELED
    assert not order.payment.is_paid
    assert item.stock == 10


def test_cash_fulfillment(browser, buyer, item):
    order = make_order(buyer, item, 'cod')
    assert browser.post(f'/payments/{order.pk}/demo/').status_code == 404
    with pytest.raises(OrderError):
        confirm_payment(order.pk)
    advance_order(order.pk, Order.Status.SHIPPED)
    with pytest.raises(OrderError):
        advance_order(order.pk, Order.Status.DELIVERED)
    confirm_payment(order.pk, cash=True)
    advance_order(order.pk, Order.Status.DELIVERED)
    order.refresh_from_db()
    assert order.status == Order.Status.DELIVERED
    assert order.payment.is_paid


def test_demo_disabled(browser, buyer, item, settings):
    order = make_order(buyer, item)
    settings.PAYMENT_DEMO_ENABLED = False
    assert browser.get(f'/payments/{order.pk}/demo/').status_code == 404
    with pytest.raises(OrderError):
        confirm_payment(order.pk)
    with pytest.raises(OrderError):
        make_order(buyer, item)
    assert make_order(buyer, item, 'cod').payment.method == 'cod'


def test_api_payment_and_invalid_method(buyer, item):
    api = APIClient()
    api.force_authenticate(buyer)
    data = {
        'shipping_address': 'Tallinn',
        'payment_method': 'invalid',
        'items': [{'product_id': item.pk, 'quantity': 2}],
    }
    assert api.post('/api/orders/', data, format='json').status_code == 400
    data['payment_method'] = 'wallet'
    response = api.post('/api/orders/', data, format='json')
    assert response.status_code == 201
    assert response.data['payment'] == {'method': 'wallet', 'is_paid': False}
    url = f'/api/orders/{response.data["id"]}/demo-pay/'
    for _ in range(2):
        response = api.post(url)
        assert response.status_code == 200
        assert response.data['payment']['is_paid'] is True


def test_analytics_uses_paid_totals_not_join_duplicates(buyer, item):
    paid = make_order(buyer, item, quantity=2)
    confirm_payment(paid.pk)
    make_order(buyer, item, 'cod', quantity=1)
    canceled = make_order(buyer, item, quantity=1)
    cancel_order(canceled.pk)
    summary = sales_summary(Order.objects.all())
    assert summary['order_count'] == 3
    assert summary['paid_count'] == 1
    assert summary['revenue'] == Decimal('25.00')
    assert summary['top_products'][0]['units'] == 2


def test_analytics_permissions(browser, buyer):
    url = '/admin/orders/order/analytics/'
    assert browser.get(url).status_code == 302
    buyer.is_staff = True
    buyer.save()
    assert browser.get(url).status_code == 403
    buyer.user_permissions.add(Permission.objects.get(codename='view_order'))
    assert browser.get(url).status_code == 200
    response = browser.get(url, {'start': 'bad-date'})
    assert response.status_code == 200
    assert response.context['form'].errors


def test_cash_admin_requires_change_permission(browser, buyer, item):
    order = make_order(buyer, item, 'cod')
    buyer.is_staff = True
    buyer.save()
    buyer.user_permissions.add(Permission.objects.get(codename='view_payment'))
    data = {'action': 'record_cash_received', '_selected_action': [order.payment.pk]}
    browser.post('/admin/payments/payment/', data)
    order.payment.refresh_from_db()
    assert not order.payment.is_paid
    buyer.user_permissions.add(Permission.objects.get(codename='change_payment'))
    browser.post('/admin/payments/payment/', data)
    order.payment.refresh_from_db()
    assert order.payment.is_paid


def test_product_history_cannot_be_deleted(buyer, item):
    make_order(buyer, item)
    with pytest.raises(ProtectedError):
        item.delete()


def test_login_rejects_external_redirect(buyer):
    client = Client()
    response = client.post(
        '/users/login/?next=https://example.org/',
        {'email': buyer.email, 'password': 'Testing-12345!'},
    )
    assert response.status_code == 302
    assert response['Location'] == '/'


def test_logout_requires_post(browser):
    assert browser.get('/users/logout/').status_code == 405
    assert browser.post('/users/logout/').status_code == 302
    assert '_auth_user_id' not in browser.session


def test_account_creates_missing_profile(browser, buyer):
    from users.models import Profile

    Profile.objects.filter(user=buyer).delete()
    response = browser.get('/users/account/')
    assert response.status_code == 200
    assert Profile.objects.filter(user=buyer).exists()


def test_profile_is_created_on_registration():
    user = get_user_model().objects.create_user(username='profile-test')
    assert user.profile.user_id == user.pk


def test_shipped_cash_order_is_not_a_purchase_until_paid(buyer, item):
    from reviews.services import has_purchased

    order = make_order(buyer, item, 'cod')
    advance_order(order.pk, Order.Status.SHIPPED)
    assert not has_purchased(buyer, item)
    confirm_payment(order.pk, cash=True)
    assert has_purchased(buyer, item)


def test_api_rating_puts_unrated_products_last(buyer, item):
    from reviews.models import Review

    Review.objects.create(user=buyer, product=item, rating=5)
    Product.objects.create(
        name='Unrated', slug='unrated-test', category=item.category, price=10, stock=2
    )
    api = APIClient()
    response = api.get(
        '/api/products/', {'category': item.category.slug, 'ordering': '-avg_rating'}
    )
    assert response.status_code == 200
    assert response.data['results'][0]['id'] == item.pk


@pytest.mark.parametrize('value', ['oops', 'NaN', 'Infinity', '-1'])
def test_catalog_invalid_price_does_not_crash(browser, value):
    assert browser.get('/', {'min_price': value}).status_code == 200


def test_popularity_and_api_price_filters(browser, buyer, item):
    order = make_order(buyer, item)
    confirm_payment(order.pk)
    response = browser.get('/', {'sort': 'popular'})
    assert response.status_code == 200
    assert next(iter(response.context['products'])).pk == item.pk
    api = APIClient()
    response = api.get('/api/products/', {'category': item.category.slug, 'min_price': 13})
    assert response.status_code == 200
    assert response.data['results'] == []


def test_cart_can_be_cleared_after_product_disappears(browser, item):
    browser.post(f'/orders/cart/add/{item.pk}/', {'quantity': 1})
    item.delete()
    assert browser.post('/orders/cart/clear/').status_code == 302
    assert browser.session.get('cart', {}) == {}


def test_openapi_schema_contains_payment_and_cart():
    from drf_spectacular.drainage import GENERATOR_STATS
    from drf_spectacular.generators import SchemaGenerator

    GENERATOR_STATS.reset()
    schema = SchemaGenerator().get_schema(request=None, public=True)
    assert '/api/cart/' in schema['paths']
    assert '/api/orders/{id}/demo-pay/' in schema['paths']
    assert 'payment_method' in schema['components']['schemas']['OrderCreate']['properties']
    review_response = schema['paths']['/api/products/{id}/reviews/']['get']['responses']['200']
    assert review_response['content']['application/json']['schema']['type'] == 'array'
    assert not GENERATOR_STATS
