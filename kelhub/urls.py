from django.urls import path
from . import views

app_name = 'kelhub'

urlpatterns = [
    path('', views.home, name='home'),
]