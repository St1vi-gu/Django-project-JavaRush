import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from products.models import Category, Product
@pytest.mark.django_db
def test_cart_rejects_more_than_stock():
    c=Category.objects.create(name="Malt",slug="malt")
    p=Product.objects.create(name="Malt",slug="malt-1",price=2,category=c,stock=1,image="x.jpg")
    client=Client()
    client.post(f"/orders/cart/add/{p.pk}/", {"quantity":2})
    assert client.session.get("cart", {}) == {}
