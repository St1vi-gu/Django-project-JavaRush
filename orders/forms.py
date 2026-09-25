from django import forms

class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ('debit', 'Debit card'),
        ('wallet', 'Wallet card'),
        ('cod', 'Cash On Delivery'),
    ]
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'Input'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'Input'}))
    city = forms.CharField(widget=forms.TextInput(attrs={'class': 'Input'}))
    address = forms.CharField(widget=forms.TextInput(attrs={'class': 'Input'}))
    payment_type = forms.CharField(widget=forms.Select(choices=PAYMENT_CHOICES))