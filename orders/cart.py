from decimal import Decimal

from products.models import Product

CART_SESSION_ID = 'cart'


class Cart:
    """Session-backed shopping cart."""

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.setdefault(CART_SESSION_ID, {})

    def add(self, product: Product, quantity: int = 1, override: bool = False) -> None:
        pid = str(product.pk)
        if pid not in self.cart:
            self.cart[pid] = {'quantity': 0, 'price': str(product.price)}
        self.cart[pid]['quantity'] = quantity if override else self.cart[pid]['quantity'] + quantity
        self.save()

    def remove(self, product: Product) -> None:
        self.cart.pop(str(product.pk), None)
        self.save()

    def save(self) -> None:
        self.session.modified = True

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids, is_active=True)

        for product in products:
            session_item = self.cart[str(product.id)]

            price = product.price

            yield {
                'product': product,
                'product_id': product.id,
                'quantity': session_item['quantity'],
                'price': price,
                'total_price': price * session_item['quantity'],
            }

    def __len__(self) -> int:
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self) -> Decimal:
        return sum(
            (item['total_price'] for item in self),
            Decimal('0'),
        )

    def clear(self) -> None:
        self.session.pop(CART_SESSION_ID, None)
        self.save()
