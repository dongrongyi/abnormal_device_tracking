
from django.urls import path

from accounts.views import CustomLoginView, RegisterView, ForgetPasswordView, CustomLogoutView, UpdatePasswordView

app_name = 'accounts'
urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("forgetPassword/", ForgetPasswordView.as_view(), name="forgetPassword"),

    path("update_password/", UpdatePasswordView.as_view(), name="update_password"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
]