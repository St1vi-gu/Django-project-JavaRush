from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from products.models import Category, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username='buyer', password='Strong-pass-172')


@pytest.fixture
def product():
    category = Category.objects.create(name='API malt', slug='api-malt')
    return Product.objects.create(
        name='API product', slug='api-product', category=category, price=Decimal('10.22'), stock=10
    )


def payload(product, quantity=2):
    return {
        'shipping_address': 'Tallinn',
        'items': [{'product_id': product.pk, 'quantity': quantity}],
    }


def test_orders_require_auth(api_client):
    assert api_client.get('/api/orders/').status_code == 401


def test_order_creation_and_cancel(api_client, user, product):
    api_client.force_authenticate(user)
    response = api_client.post('/api/orders/', payload(product), format='json')
    assert response.status_code == 201, response.data
    assert response.data['total_price'] == '20.44'
    assert response.data['status'] == 'pending'
    product.refresh_from_db()
    assert product.stock == 8
    order_id = response.data['id']
    assert api_client.delete(f'/api/orders/{order_id}/').status_code == 204
    product.refresh_from_db()
    assert product.stock == 10
    assert api_client.delete(f'/api/orders/{order_id}/').status_code == 400
    product.refresh_from_db()
    assert product.stock == 10


@pytest.mark.parametrize('kind', ['stock', 'missing', 'duplicate', 'empty', 'zero', 'inactive'])
def test_invalid_order_rolls_back(api_client, user, product, kind):
    api_client.force_authenticate(user)
    data = payload(product)
    if kind == 'stock':
        data['items'][0]['quantity'] = 11
    elif kind == 'missing':
        data['items'].append({'product_id': 999999, 'quantity': 1})
    elif kind == 'duplicate':
        data['items'] *= 6
    elif kind == 'empty':
        data['items'] = []
    elif kind == 'zero':
        data['items'][0]['quantity'] = 0
    else:
        product.is_active = False
        product.save()
    response = api_client.post('/api/orders/', data, format='json')
    assert response.status_code == 400, response.data
    assert not Order.objects.filter(user=user).exists()
    product.refresh_from_db()
    assert product.stock == 10


def test_order_ownership(api_client, user, product):
    other = get_user_model().objects.create_user(username='other')
    order = Order.objects.create(user=other, total_price=0)
    api_client.force_authenticate(user)
    assert api_client.get(f'/api/orders/{order.pk}/').status_code == 404
    assert api_client.delete(f'/api/orders/{order.pk}/').status_code == 404
    assert api_client.patch(f'/api/orders/{order.pk}/', {'status': 'paid'}).status_code == 405


def test_catalog_and_reviews(api_client, user, product):
    assert api_client.get('/api/categories/').status_code == 200
    response = api_client.get(
        '/api/products/', {'search': 'API product', 'category': 'api-malt', 'ordering': 'price'}
    )
    assert response.status_code == 200
    assert [p['id'] for p in response.data['results']] == [product.pk]
    api_client.force_authenticate(user)
    url = f'/api/products/{product.pk}/reviews/'
    assert api_client.post(url, {'rating': 5, 'comments': 'Good'}).status_code == 403
    order = Order.objects.create(user=user, total_price=product.price, status=Order.Status.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
    assert api_client.post(url, {'rating': 5, 'comments': 'Good'}).status_code == 201
    assert api_client.post(url, {'rating': 4}).status_code == 400
    assert api_client.get(url).data[0]['comments'] == 'Good'


def test_cart(api_client, product):
    assert (
        api_client.post('/api/cart/', {'product_id': product.pk, 'quantity': 2}).status_code == 200
    )
    assert (
        api_client.post('/api/cart/', {'product_id': product.pk, 'quantity': 9}).status_code == 400
    )
    url = f'/api/cart/{product.pk}/'
    assert api_client.patch(url, {'quantity': 3}, format='json').status_code == 200
    assert api_client.patch(url, {'quantity': 0}, format='json').status_code == 400
    assert api_client.get('/api/cart/').data['items'][0]['quantity'] == 3
    assert api_client.delete(url).status_code == 204
    assert api_client.get('/api/cart/').data['items'] == []


def test_register_and_jwt(api_client):
    data = {'email': 'NEW@example.com', 'password': 'Complex-Password-172!'}
    response = api_client.post('/api/users/register/', data)
    assert response.status_code == 201, response.data
    assert 'password' not in response.data
    assert api_client.post('/api/users/register/', data).status_code == 400
    response = api_client.post(
        '/api/users/login/', {'username': 'new@example.com', 'password': data['password']}
    )
    assert response.status_code == 200, response.data
    assert (
        api_client.post(
            '/api/users/token/refresh/', {'refresh': response.data['refresh']}
        ).status_code
        == 200
    )


def test_pages(api_client):
    for url in ['/', '/orders/cart/', '/users/login/', '/api/docs/']:
        assert api_client.get(url).status_code == 200, url
