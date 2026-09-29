import pytest

from products.models import Category, Product


@pytest.mark.django_db
def test_product_absolute_url():
    c = Category.objects.create(name='Hops', slug='test-hops')
    p = Product.objects.create(
        name='Citra', slug='test-citra', price=5, category=c, stock=2, image='x.jpg'
    )
    assert p.get_absolute_url() == '/product/test-citra/'
