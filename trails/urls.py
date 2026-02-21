from django.urls import path
from . import views

urlpatterns = [
    path('',                                                  views.trail_list,      name='trail_list'),
    path('create/',                                           views.trail_create,    name='trail_create'),
    path('<int:trail_id>/',                                   views.trail_detail,    name='trail_detail'),
    path('<int:trail_id>/lesson/<int:lesson_id>/',            views.lesson_session,  name='lesson_session'),
    path('<int:trail_id>/lesson/<int:lesson_id>/answer/',     views.lesson_answer,   name='lesson_answer'),
    path('<int:trail_id>/lesson/<int:lesson_id>/complete/',   views.lesson_complete, name='lesson_complete'),
]
