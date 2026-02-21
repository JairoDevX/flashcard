from django.contrib import admin
from django.urls import path, include
from accounts.urls import api_urlpatterns

urlpatterns = [
    path("admin/",      admin.site.urls),
    path("accounts/",   include("accounts.urls")),
    path("api/auth/",   include((api_urlpatterns, "api_auth"))),
    path("decks/",      include("decks.urls")),
    path("study/",      include("study.urls")),
    path("analytics/",  include("analytics.urls")),
    path("trilhas/",    include("trails.urls")),
    path("",            include("decks.urls_dashboard")),
]
