from django.urls import path

from .views import AuthTokenRefreshView, AuthTokenView, MeView, RegisterView, UserListView

urlpatterns = [
    path("login/", AuthTokenView.as_view(), name="login"),
    path("refresh/", AuthTokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", UserListView.as_view(), name="users"),
    path("register/", RegisterView.as_view(), name="register"),
]
