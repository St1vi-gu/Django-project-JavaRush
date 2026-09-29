from django import forms
from django.conf import settings

from payments.models import Payment


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    phone_number = forms.CharField(max_length=30)
    city = forms.CharField(max_length=100)
    address = forms.CharField(max_length=300)
    payment_type = forms.ChoiceField(choices=Payment.Method.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.PAYMENT_DEMO_ENABLED:
            self.fields['payment_type'] = forms.ChoiceField(
                choices=[(Payment.Method.COD, 'Оплата при получении')]
            )
