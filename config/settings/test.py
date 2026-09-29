from .base import *

SECRET_KEY = 'isolated-test-key-only-at-least-32-characters'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

PAYMENT_DEMO_ENABLED = True
