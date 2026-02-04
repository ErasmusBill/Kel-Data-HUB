from django.urls import path
from . import views
from users.views import reset_password, reset_password_request

app_name = 'users'

urlpatterns = [
    path('register/', views.create_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('change-password/', views.change_password, name='change_password'),
    path('update-user-profile/<uuid:user_id>',views.update_user_profile, name='update-user-profile'),
    path('reset-password',views.reset_password,name='reset-password'),
    path('request-password-rese/',views.reset_password_request, name="reset_password_request"),
    path('logout/', views.logout_user, name='logout'),
    # path('user-dashboard/',views.user_dashboard, name='dashboard'),
    path('admin-dashboard/',views.admin_dashboard,name='admin-dashboard'),
    path('display_data_plans/<str:network>/',views.display_data_plans_view, name='display-data-plans'),
    
]