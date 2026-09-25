from django.db import models
from django.conf import settings
# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='profile')
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f'Profile of {self.user}'