from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
app_name = "users"
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("account/", views.account_view, name="account"),
    path("password-change/", auth_views.PasswordChangeView.as_view(
        template_name="password_change.html", success_url="/users/account/"), name="password_change"),
]
