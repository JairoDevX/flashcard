from django.urls import path
from . import views
from .ai_views import ai_generate

urlpatterns = [
    path('', views.deck_list, name='deck_list'),
    path('new/', views.deck_create, name='deck_create'),
    path('<int:pk>/', views.deck_detail, name='deck_detail'),
    path('<int:pk>/edit/', views.deck_edit, name='deck_edit'),
    path('<int:pk>/delete/', views.deck_delete, name='deck_delete'),
    path('<int:deck_pk>/cards/new/', views.card_create, name='card_create'),
    path('<int:deck_pk>/cards/<int:pk>/edit/', views.card_edit, name='card_edit'),
    path('<int:deck_pk>/cards/<int:pk>/delete/', views.card_delete, name='card_delete'),
    path('<int:deck_pk>/ai-generate/', ai_generate, name='ai_generate'),
    path('vocabulary/', views.vocabulary_list, name='vocabulary'),
]
