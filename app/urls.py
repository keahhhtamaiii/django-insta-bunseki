from django.urls import path
from app import views
from . import views
from .views import CallbackView

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('hashtag/', views.HashtagView.as_view(), name='hashtag'),
    path('callback/', CallbackView.as_view(), name='callback'),
]
