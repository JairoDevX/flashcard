from django.urls import path
from . import views

urlpatterns = [
    path('',            views.analytics_dashboard, name='analytics'),
    path('leaderboard/', views.leaderboard,         name='leaderboard'),
]
