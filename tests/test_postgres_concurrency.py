from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection

from orders.models import Order
from orders.services import OrderError, cancel_order, place_order
from payments.services import confirm_payment
from products.models import Category, Product

pytestmark = pytest.mark.django_db(transaction=True)


def run_parallel(*actions):
    barrier = Barrier(len(actions))

    def run(action):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                action()
                return 'ok'
            except OrderError:
                return 'rejected'
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        return list(executor.map(run, actions))


@pytest.fixture
def purchase():
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL row locks; covered by the PostgreSQL CI job.')
    user = get_user_model().objects.create_user(username='concurrent')
    category = Category.objects.create(name='Concurrent', slug='concurrent')
    product = Product.objects.create(
        name='Concurrent', slug='concurrent', category=category, price=Decimal('5.00'), stock=1
    )
    return user, product


def test_last_unit_can_only_be_ordered_once(purchase):
    user, product = purchase

    def buy():
        place_order(user, [{'product_id': product.pk, 'quantity': 1}], 'Tallinn', 'cod')

    results = run_parallel(buy, buy)
    assert sorted(results) == ['ok', 'rejected']
    product.refresh_from_db()
    assert product.stock == 0
    assert Order.objects.filter(user=user).count() == 1


def test_double_cancellation_returns_stock_once(purchase):
    user, product = purchase
    order = place_order(user, [{'product_id': product.pk, 'quantity': 1}], 'Tallinn', 'cod')
    results = run_parallel(lambda: cancel_order(order.pk), lambda: cancel_order(order.pk))
    assert sorted(results) == ['ok', 'rejected']
    product.refresh_from_db()
    assert product.stock == 1


def test_payment_cancellation_race_is_consistent(purchase):
    user, product = purchase
    order = place_order(user, [{'product_id': product.pk, 'quantity': 1}], 'Tallinn', 'debit')
    results = run_parallel(lambda: cancel_order(order.pk), lambda: confirm_payment(order.pk))
    assert sorted(results) == ['ok', 'rejected']
    order.refresh_from_db()
    product.refresh_from_db()
    if order.status == Order.Status.PAID:
        assert order.payment.is_paid
        assert product.stock == 0
    else:
        assert order.status == Order.Status.CANCELED
        assert not order.payment.is_paid
        assert product.stock == 1
