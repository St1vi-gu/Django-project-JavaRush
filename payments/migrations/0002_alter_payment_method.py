from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(choices=[('debit', 'Тестовая оплата'), ('wallet', 'Тест оплата кошельком )'), ('cod', 'Оплата при получении')], max_length=20),
        ),
    ]
