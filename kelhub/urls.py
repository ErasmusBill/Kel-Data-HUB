from django.urls import path
from . import views

app_name = 'kelhub'

urlpatterns = [
    path('', views.home, name='home'),
    path('packages/<str:network>/', views.get_all_data_plans, name='data_plans'),
]