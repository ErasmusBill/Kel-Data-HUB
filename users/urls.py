from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.create_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('change-password/', views.change_password, name='change_password'),
    path('logout/', views.logout_user, name='logout'),
    
]