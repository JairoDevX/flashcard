from django.urls import path
from . import views

urlpatterns = [
    path('', views.study_home, name='study_home'),
    path('session/', views.study_session, name='study_session'),
    path('answer/', views.study_answer, name='study_answer'),
    path('complete/', views.study_complete, name='study_complete'),
    path('restart/', views.study_restart, name='study_restart'),
    path('gesture/', views.gesture_session, name='gesture_session'),
    path('gesture/answer/', views.gesture_answer, name='gesture_answer'),
    path('gesture/complete/', views.gesture_complete, name='gesture_complete'),
]
