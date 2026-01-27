from django.urls import path
from . import views

app_name = 'kelhub'

urlpatterns = [
    path('', views.home, name='home'),
    path('packages/<str:network>/', views.data_plans_view, name='data_plans'),
    path('purchase/<int:bundle_id>/', views.purchase_bundle, name='purchase_bundle'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('my-orders/', views.user_orders, name='user_orders'),
]

