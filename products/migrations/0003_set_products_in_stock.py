from django.db import migrations, models


def set_products_in_stock(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    Product.objects.update(stock=100, is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0002_seed_initial_catalog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='stock',
            field=models.PositiveIntegerField(default=100),
        ),
        migrations.RunPython(set_products_in_stock, migrations.RunPython.noop),
    ]
