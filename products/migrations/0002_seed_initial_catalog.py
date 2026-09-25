from django.db import migrations


CATEGORIES = (
    ('Hops', 'hops'),
    ('Malts', 'malts'),
    ('Yeast', 'yeast'),
    ('Adjuncts & Kits', 'adjuncts-kits'),
)

PRODUCTS = (
    ('Citra Hops', 'citra-hops', 'Ideal for IPAs and Pale Ales', '5.99', 'hops', 'citra_hops.jpg'),
    ('Maris Otter Pale Malt', 'maris-otter-malt', 'Perfect for traditional ales', '2.50', 'malts', 'maris_otter_malt.jpg'),
    ('SafAle US-05 Dry Ale Yeast', 'safale-us05-yeast', 'Clean fermenting American ale yeast', '3.25', 'yeast', 'safale_us05_yeast.jpg'),
    ('Cascade Hops', 'cascade-hops', 'Great for dry hopping', '7.49', 'hops', 'cascade_hops.jpg'),
    ('Caramel Malt 60L', 'caramel-malt', 'Head retention in darker beers', '3.00', 'malts', 'caramel_malt.jpg'),
    ('Saaz Hops', 'saaz-hops', 'Essential for Lagers', '4.75', 'hops', 'saaz_hops.jpg'),
    ('Pilsner Malt', 'pilsner-malt', 'Foundation for lagers and pilsners', '2.20', 'malts', 'pilsner_malt.jpg'),
    ('Imperial Organic Yeast A07', 'imperial-yeast', 'American ales with citrus notes', '8.99', 'yeast', 'imperial_yeast.jpg'),
    ('Centennial Hops', 'centennial-hops', 'Often called "Super Cascade"', '6.20', 'hops', 'centennial_hops.jpg'),
    ('Mosaic Hops', 'mosaic-hops', 'Ideal for IPAs and Pale Ales', '9.50', 'hops', 'mosaic_hops.jpg'),
    ('West Coast IPA - All-Grain Kit', 'west-coast-ipa-kit', 'West Coast IPA', '60.00', 'adjuncts-kits', 'ipa_kit.jpg'),
    ('Unmalted Wheat', 'unmalted-wheat', 'Belgian Witbier', '1.80', 'adjuncts-kits', 'unmalted_wheat.jpg'),
)


def seed_catalog(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')

    categories = {}
    for name, slug in CATEGORIES:
        category, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
        categories[slug] = category

    for name, slug, description, price, category_slug, image_name in PRODUCTS:
        Product.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'description': description,
                'price': price,
                'category': categories[category_slug],
                'image': f'products/catalog/{image_name}',
                'stock': 0,
                'is_active': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
