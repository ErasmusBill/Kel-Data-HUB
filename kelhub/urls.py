from django.urls import path
from . import views

app_name = 'kelhub'

urlpatterns = [
    
    # Home
    path('', views.home, name='home'),
    path('plans/<str:network>/', views.data_plans_view, name='data_plans'),
    path('purchase_data/<int:bundle_id>/', views.purchase_data_view, name='purchase_data'),
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('order/<uuid:order_id>/success/', views.order_success_view, name='order_success'),
    
    path('track/', views.track_order, name='track_order'),
    
    path('api/wallet/balance/', views.check_wallet_balance, name='check_balance'),
    
   
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.deposit_view, name='deposit'),
    path('wallet/deposit/callback/', views.deposit_callback, name='deposit_callback'),
    
    path('order/<uuid:order_id>/retry/', views.retry_failed_order, name='retry_order'),
    path('orders/', views.order_history_view, name='order_history'),
    
   
    path('admin/sync-bundles/', views.sync_bundles_view, name='sync_bundles'),
    
]