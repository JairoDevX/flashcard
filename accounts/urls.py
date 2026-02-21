from django.urls import path
from . import views

# Web auth
urlpatterns = [
    path("login/",    views.login_view,    name="login"),
    path("logout/",   views.logout_view,   name="logout"),
    path("register/", views.register_view, name="register"),
    path("profile/",  views.profile_view,  name="profile"),
]

# JWT API endpoints
api_urlpatterns = [
    path("token/",         views.api_token_obtain,  name="api_token_obtain"),
    path("token/refresh/", views.api_token_refresh,  name="api_token_refresh"),
    path("me/",            views.api_me,             name="api_me"),
]
