from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("set-choice/", views.set_choice, name="set_choice"),
    path("chat/", views.chat, name="chat"),
]